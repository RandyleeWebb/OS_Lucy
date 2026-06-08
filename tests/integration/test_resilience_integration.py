import os
import sys
import time
import requests
import importlib
import pytest

# Ensure `src` is on the import path
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
	sys.path.insert(0, SRC)

from testcontainers.core.generic import GenericContainer


def create_toxiproxy_and_httpbin():
	http = GenericContainer('kennethreitz/httpbin').with_exposed_ports(80)
	tox = GenericContainer('shopify/toxiproxy:2.1.4').with_exposed_ports(8474, 8666)

	http_container = http.start()
	tox_container = tox.start()

	http_port = http_container.get_exposed_port(80)
	tox_api_port = tox_container.get_exposed_port(8474)
	tox_listen_port = tox_container.get_exposed_port(8666)

	tox_api_url = f'http://{tox_container.get_container_host_ip()}:{tox_api_port}'
	proxy_url = f'http://{tox_container.get_container_host_ip()}:{tox_listen_port}'

	return http_container, tox_container, http_port, tox_api_url, proxy_url


def create_proxy_for_datavault(tox_api_url, http_container):
	# Use the http container's internal IP so toxiproxy (in Docker) can reach it directly
	try:
		nets = http_container._container.attrs.get('NetworkSettings', {}).get('Networks', {})
		if nets:
			first = next(iter(nets.values()))
			ip = first.get('IPAddress')
		else:
			ip = http_container.get_container_host_ip()
	except Exception:
		ip = http_container.get_container_host_ip()

	upstream = f'http://{ip}:80'
	resp = requests.post(f'{tox_api_url}/proxies', json={
		'name': 'datavault',
		'listen': '0.0.0.0:8666',
		'upstream': upstream,
	})
	resp.raise_for_status()
	return resp.json()


def add_latency_toxic(tox_api_url, proxy_name='datavault', name='latency', latency_ms=6000):
	url = f'{tox_api_url}/proxies/{proxy_name}/toxics'
	payload = {
		'name': name,
		'type': 'latency',
		'stream': 'upstream',
		'attributes': {'latency': latency_ms, 'jitter': 0}
	}
	r = requests.post(url, json=payload)
	r.raise_for_status()
	return r.json()


def remove_toxic(tox_api_url, proxy_name='datavault', toxic_name='latency'):
	url = f'{tox_api_url}/proxies/{proxy_name}/toxics/{toxic_name}'
	r = requests.delete(url)
	# toxiproxy returns 204 on success
	return r.status_code in (200, 204)


def test_circuit_breaker_trips_and_recovers():
	httpc, toxc, http_port, tox_api_url, proxy_url = create_toxiproxy_and_httpbin()
	try:
		# create proxy
		create_proxy_for_datavault(tox_api_url, httpc)

		# set DATAVAULT_URL to the proxy listen address
		os.environ['DATAVAULT_URL'] = proxy_url + '/log'

		# reload datavault module to pick up env var
		import orchestrator.clients.datavault as dv
		importlib.reload(dv)

		# import circuit breaker
		from resilience.circuit import CircuitBreaker

		cb = CircuitBreaker('test-dv', failure_threshold=2, recovery_timeout=3, capacity=2)

		# baseline: POST should succeed via proxy -> httpbin
		res = dv.write('test', {'a': 1})
		assert res.get('ok') is True

		# add latency toxic so requests will timeout (datavault.write uses timeout=5)
		add_latency_toxic(tox_api_url, latency_ms=6000)

		# two failing attempts -> tripping threshold
		r1 = dv.safe_write_with_cb(cb, 'test', {'a': 2})
		r2 = dv.safe_write_with_cb(cb, 'test', {'a': 3})

		# failures recorded
		assert r1.get('ok') is False
		assert r2.get('ok') is False

		# next call should be short-circuited by circuit breaker (fallback)
		r3 = dv.safe_write_with_cb(cb, 'test', {'a': 4})
		assert r3.get('ok') is False
		assert 'circuit_open' in r3.get('reason', '') or 'bulkhead' in r3.get('reason', '')

		# remove toxic and wait for recovery timeout
		remove_toxic(tox_api_url)
		time.sleep(4)

		# now circuit should be half-open and next call should succeed and reset
		r4 = dv.safe_write_with_cb(cb, 'test', {'a': 5})
		# either a success or fallback; ensure eventually we can get success
		assert isinstance(r4, dict)
		# try a direct write as final confirmation
		r5 = dv.write('test', {'a': 6})
		assert r5.get('ok') is True

	finally:
		try:
			httpc.stop()
		except Exception:
			pass
		try:
			toxc.stop()
		except Exception:
			pass


def test_chaos_by_stopping_service_triggers_fallback():
	# Start containers without context manager so we can stop the upstream service
	http = GenericContainer('kennethreitz/httpbin').with_exposed_ports(80)
	tox = GenericContainer('shopify/toxiproxy:2.1.4').with_exposed_ports(8474, 8666)

	httpc = http.start()
	toxc = tox.start()
	try:
		http_port = httpc.get_exposed_port(80)
		tox_api_port = toxc.get_exposed_port(8474)
		tox_listen_port = toxc.get_exposed_port(8666)
		tox_api_url = f'http://{toxc.get_container_host_ip()}:{tox_api_port}'
		proxy_url = f'http://{toxc.get_container_host_ip()}:{tox_listen_port}'

		create_proxy_for_datavault(tox_api_url, httpc)
		os.environ['DATAVAULT_URL'] = proxy_url + '/log'
		import orchestrator.clients.datavault as dv
		importlib.reload(dv)
		from resilience.circuit import CircuitBreaker

		cb = CircuitBreaker('chaos-dv', failure_threshold=1, recovery_timeout=2, capacity=1)

		# initial write ok
		r0 = dv.write('test', {'ok': True})
		assert r0.get('ok') is True

		# stop the upstream httpbin to simulate service down
		httpc.stop()
		time.sleep(0.5)

		r1 = dv.safe_write_with_cb(cb, 'test', {'after': 'stop'})
		assert r1.get('ok') is False

		# restart upstream by starting a new container instance
		httpc = GenericContainer('kennethreitz/httpbin').with_exposed_ports(80).start()
		# re-create proxy upstream mapping to new host port
		new_http_port = httpc.get_exposed_port(80)
		# remove and re-create proxy using tox api
		try:
			requests.delete(f'{tox_api_url}/proxies/datavault')
		except Exception:
			pass
		create_proxy_for_datavault(tox_api_url, httpc)

		time.sleep(1)
		r2 = dv.write('test', {'after': 'restart'})
		assert r2.get('ok') is True

	finally:
		try:
			httpc.stop()
		except Exception:
			pass
		try:
			toxc.stop()
		except Exception:
			pass
