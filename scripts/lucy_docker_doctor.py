#!/usr/bin/env python3
"""Doctor tool for the Lucy docker stack.

Checks:
 - Docker daemon reachable
 - docker compose available
 - docker compose ps parsed for core services
 - /health endpoints for known services (both container hostnames and localhost)
"""
import shutil
import subprocess
import sys
import json
import time
from typing import Dict, List

CORE_SERVICES = {
	"datavault": ["localhost", 8012],
	"safeguard": ["localhost", 8013],
	"evolutionary-prompt": ["localhost", 8014],
	"perfmon": ["localhost", 8015],
	"orchestrator": ["localhost", 8020],
	"homeostasis": ["localhost", 8030],
}


def check_docker_daemon() -> bool:
	# try docker info
	try:
		out = subprocess.check_output(["docker", "info"], stderr=subprocess.STDOUT, timeout=5)
		return True
	except Exception as e:
		print("Docker daemon unreachable:", str(e))
		return False


def check_docker_compose() -> bool:
	if shutil.which("docker-compose") or shutil.which("docker"):
		return True
	print("docker compose not found in PATH")
	return False


def run_compose_ps() -> List[str]:
	try:
		# prefer `docker compose ps` if available
		if shutil.which("docker"):
			p = subprocess.run(["docker", "compose", "ps", "--format", "json"], capture_output=True, text=True, timeout=8)
			if p.returncode == 0:
				try:
					data = json.loads(p.stdout)
					return [f"{c.get('Name')}:{c.get('State')}" for c in data]
				except Exception:
					return p.stdout.splitlines()
		if shutil.which("docker-compose"):
			p = subprocess.run(["docker-compose", "ps"], capture_output=True, text=True, timeout=8)
			if p.returncode == 0:
				return p.stdout.splitlines()
	except Exception as e:
		print("docker compose ps failed:", e)
	return []


def check_health(host: str, port: int) -> bool:
	import socket
	import urllib.request
	url = f"http://{host}:{port}/health"
	try:
		with urllib.request.urlopen(url, timeout=4) as r:
			data = r.read().decode()
			return True
	except Exception:
		return False


def tail_logs(service: str, lines: int = 30):
	try:
		p = subprocess.run(["docker", "compose", "logs", "--tail", str(lines), service], capture_output=True, text=True, timeout=10)
		if p.returncode == 0:
			print(p.stdout)
		else:
			print(f"Failed to fetch logs for {service}: rc={p.returncode}")
	except Exception as e:
		print(f"Cannot tail logs for {service}: {e}")


def main():
	print("Lucy Docker Doctor")
	ok = check_docker_daemon()
	compose_ok = check_docker_compose()
	print(f"Docker daemon reachable: {ok}")
	print(f"docker compose available: {compose_ok}")

	ps = run_compose_ps()
	print("\n== docker compose ps ==")
	for l in ps:
		print(l)

	print("\n== Service health checks ==")
	for name, (host, port) in CORE_SERVICES.items():
		# try container DNS first
		container_host = name
		healthy = False
		for h in (container_host, host):
			if check_health(h, port):
				print(f"{name}: ok ({h}:{port})")
				healthy = True
				break
		if not healthy:
			print(f"{name}: NOT reachable on {host}:{port}")
			print("Tail recent logs:\n")
			tail_logs(name, lines=20)


if __name__ == '__main__':
	main()
