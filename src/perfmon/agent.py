import time
import psutil
import requests
import os

DATAVAULT_URL = os.environ.get("DATAVAULT_URL", "http://datavault:8012/log")
EP_URL = os.environ.get("EP_URL", "http://evolutionary-prompt:8014/prompt/update")

def sample_and_report(interval=5):
	while True:
		cpu = psutil.cpu_percent(interval=None)
		mem = psutil.virtual_memory().percent
		t = {"cpu": cpu, "mem": mem}
		# write to datavault
		try:
			# include optional agent_id to simulate per-agent telemetry streams
			requests.post(DATAVAULT_URL, json={"source": "perfmon", "payload": {"cpu": cpu, "mem": mem, "agent_id": os.environ.get('PERF_AGENT_ID','agent-1')}})
		except Exception:
			pass
		# send to prompt engine
		try:
			requests.post(EP_URL, json={"P_t": {"cpu": 0.5, "mem": 0.5}, "T_t": t})
		except Exception:
			pass
		time.sleep(interval)

if __name__ == '__main__':
	sample_and_report()


# lightweight http health endpoint for perfmon agent container
try:
	from fastapi import FastAPI
	perf_app = FastAPI()

	@perf_app.get("/health")
	async def health():
		return {"status": "ok", "service": "perfmon"}

	if os.environ.get("PERFMON_RUN_SERVER") == "1":
		import uvicorn
		uvicorn.run(perf_app, host="0.0.0.0", port=int(os.environ.get("PERFMON_PORT", 8015)))
except Exception:
	pass
