import os
import sys
import time
import requests
import importlib

# ensure src on path
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
	sys.path.insert(0, SRC)

from testcontainers.core.generic import GenericContainer


def start_orchestrator_with_deps():
	# start httpbin as datavault
	datavault = GenericContainer('kennethreitz/httpbin').with_exposed_ports(80)
	safeguard = GenericContainer('kennethreitz/httpbin').with_exposed_ports(80)
	trusted = GenericContainer('kennethreitz/httpbin').with_exposed_ports(80)
	tox = GenericContainer('shopify/toxiproxy:2.1.4').with_exposed_ports(8474, 8666)

	dvc = datavault.start()
	sgc = safeguard.start()
	txc = trusted.start()
	toxc = tox.start()

	# orchestrator image build requires Docker; use local Python invocation of server with env pointing to containers
	return dvc, sgc, txc, toxc


def create_proxy(tox_api_url, name: str, target_container):
	# resolve target internal ip
	nets = target_container._container.attrs.get('NetworkSettings', {}).get('Networks', {})
	if nets:
		ip = next(iter(nets.values())).get('IPAddress')
	else:
		ip = target_container.get_container_host_ip()
	upstream = f'http://{ip}:80'
	# choose listen ports per service to avoid collisions
	listen_map = {
		'datavault': '0.0.0.0:8666',
		'safeguard': '0.0.0.0:8667',
		'trusted-executor': '0.0.0.0:8668'
	}
	listen = listen_map.get(name, '0.0.0.0:0')
	resp = requests.post(f'{tox_api_url}/proxies', json={
		'name': name,
		'listen': listen,
		'upstream': upstream
	})
	resp.raise_for_status()
	return resp.json()


def wait_for_url(url, timeout=10):
	deadline = time.time() + timeout
	while time.time() < deadline:
		try:
			r = requests.get(url, timeout=1)
			if r.status_code == 200:
				return True
		except Exception:
			pass
		time.sleep(0.5)
	return False


def test_orchestrator_end_to_end():
	dvc, sgc, txc, toxc = start_orchestrator_with_deps()
	try:
		tox_api_port = toxc.get_exposed_port(8474)
		tox_host = toxc.get_container_host_ip()
		tox_api_url = f'http://{tox_host}:{tox_api_port}'

		# create proxies for datavault, safeguard, trusted executor
		create_proxy(tox_api_url, 'datavault', dvc)
		create_proxy(tox_api_url, 'safeguard', sgc)
		create_proxy(tox_api_url, 'trusted-executor', txc)

		# configure env for local orchestrator invocation
		os.environ['DATAVAULT_URL'] = f'http://{tox_host}:8666/log'
		os.environ['SAFEGUARD_URL'] = f'http://{tox_host}:8666/audit'
		os.environ['TRUSTED_EXECUTOR_URL'] = f'http://{tox_host}:8666/execute'

		# run orchestrator server in-process using subprocess; ensure PYTHONPATH points to src
		import subprocess
		env = os.environ.copy()
		env['PYTHONPATH'] = SRC
		p = subprocess.Popen([sys.executable, '-m', 'orchestrator.server'], env=env)

		try:
			# wait for orchestrator health
			assert wait_for_url('http://127.0.0.1:8020/health', timeout=15)

			# call resilience selftest endpoint
			r = requests.get('http://127.0.0.1:8020/resilience/selftest', timeout=10)
			assert r.status_code == 200
			jr = r.json()
			assert 'report' in jr

			# call resilience score
			r2 = requests.get('http://127.0.0.1:8020/resilience/score', timeout=5)
			assert r2.status_code == 200

			# test execute_wasm with a bogus wasm to hit validation path
			payload = {"wasm_module": "invalid-base64", "agent_id": "test"}
			r3 = requests.post('http://127.0.0.1:8020/execute_wasm', json=payload, timeout=5)
			assert r3.status_code == 200

		finally:
			p.terminate()
			p.wait(timeout=5)

	finally:
		try:
			dvc.stop()
		except Exception:
			pass
		try:
			sgc.stop()
		except Exception:
			pass
		try:
			txc.stop()
		except Exception:
			pass
		try:
			toxc.stop()
		except Exception:
			pass
