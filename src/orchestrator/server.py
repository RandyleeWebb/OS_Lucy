from fastapi import FastAPI
from pydantic import BaseModel
from .replication_flow import replicate_agent
from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi import BackgroundTasks
from .ollama_client import CLIENT as OLLAMA_CLIENT, autodetect as ollama_autodetect, status as ollama_status
from .clients.trusted_executor import safe_execute_wasm
from ..resilience.circuit import CircuitBreaker, CircuitOpenException
from .middleware.safeguard_middleware import verify_safeguard_decision
from .middleware.auth_mw import require_auth, get_current_actor
from fastapi import Depends, Request

# simple global breakers for dependent services
DATAVAULT_CB = CircuitBreaker('datavault', failure_threshold=3, recovery_timeout=10, capacity=5)
SAFEGUARD_CB = CircuitBreaker('safeguard', failure_threshold=3, recovery_timeout=10, capacity=5)
TRUSTED_EXECUTOR_CB = CircuitBreaker('trusted_executor', failure_threshold=3, recovery_timeout=10, capacity=3)

from .clients import datavault as dv_client
from .clients import safeguard as sg_client
from ..resilience import selftest as resilience_selftest
from ..resilience import battlemaster as battlemaster


app = FastAPI()
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.get('/health')
async def health():
	return {"status": "ok", "service": "orchestrator"}


@app.get('/debug/stack')
async def debug_stack():
	services = {
		"datavault": "http://datavault:8012/health",
		"safeguard": "http://safeguard:8013/health",
		"evolutionary_prompt": "http://evolutionary-prompt:8014/health",
		"perfmon": "http://perfmon:8015/health",
		"orchestrator": "http://orchestrator:8020/health",
		"homeostasis": "http://homeostasis:8030/health",
	}
	import httpx
	results = {}
	async with httpx.AsyncClient(timeout=5.0) as client:
		for name, url in services.items():
			try:
				r = await client.get(url)
				if r.status_code == 200:
					results[name] = "ok"
				else:
					results[name] = f"error:{r.status_code}"
			except Exception:
				results[name] = "down"
	return results


@app.get('/ollama/status')
async def ollama_status_endpoint():
	# return the detected ollama status
	# require auth
	auth_ok, auth_info = require_auth({k:v for k,v in ( ("authorization", "") ,)})
	# NOTE: in FastAPI we'd normally use a dependency and Request object; MVP uses header passthrough in clients
	try:
		s = await ollama_status()
		return {"ok": True, "ollama": s}
	except Exception:
		return {"ok": False, "ollama": None}


@app.get('/resilience/score')
async def resilience_score():
	# Basic scoring: prefer open circuits = worse score, capacity utilization not yet tracked.
	score = 100
	details = {}
	for name, cb in [('datavault', DATAVAULT_CB), ('safeguard', SAFEGUARD_CB), ('trusted_executor', TRUSTED_EXECUTOR_CB)]:
		st = cb.state
		if st == 'OPEN':
			score -= 30
		elif st == 'HALF_OPEN':
			score -= 10
		details[name] = st
	return {"score": max(0, score), "details": details}


@app.on_event('startup')
async def orchestrator_startup():
	# attempt to autodetect Ollama on startup
	try:
		await ollama_autodetect()
	except Exception:
		pass


@app.post('/inject_proactive')
async def inject_proactive(background: BackgroundTasks, payload: dict, request: Request, actor: str = Depends(get_current_actor)):
	# simple endpoint to accept proactive tasks from homeostasis
	# write into datavault and enqueue into orchestrator queue (mock)
	try:
		# enforce auth by extracting actor_id if present in payload or from token when integrated
		actor_id = payload.get('agent_id')
		if auth_ok and 'actor' in auth_info:
			actor_id = auth_info.get('actor')
		# enforce SafeGuard decision for proactive injections
		sg_res = await verify_safeguard_decision(actor_id or '', 'inject_proactive', payload)
		if not sg_res.get('ok', True):
			return {"ok": False, "reason": "safeguard_denied", "details": sg_res}
		# write audit/event
		import requests
		DATAVAULT = os.environ.get('DATAVAULT_URL','http://datavault:8012/log')
		requests.post(DATAVAULT, json={"source":"homeostasis", "payload": payload})
	except Exception:
		pass
	return {"ok": True}


@app.get('/resilience/selftest')
async def resilience_selftest_endpoint():
	# run quick synthetic checks
	try:
		report = resilience_selftest.run_selftest_sync()
		# log to datavault best-effort
		try:
			dv_client.write('orchestrator_selftest', report)
		except Exception:
			pass
		return {"ok": True, "report": report}
	except Exception as e:
		return {"ok": False, "error": str(e)}


class ChaosReq(BaseModel):
	action: str
	service: str


@app.post('/resilience/chaos')
async def resilience_chaos(req: ChaosReq, request: Request, actor: str = Depends(get_current_actor)):
	# simple battle master wrapper
	try:
		if req.action == 'kill':
			r = battlemaster.kill_service(req.service)
		elif req.action == 'start':
			r = battlemaster.start_service(req.service)
		elif req.action == 'restart':
			r = battlemaster.restart_service(req.service)
		elif req.action == 'latency':
			r = battlemaster.inject_latency(req.service)
		else:
			return {"ok": False, "reason": "unknown_action"}
		# best-effort log
		try:
			dv_client.write('orchestrator_chaos', {"action": req.action, "service": req.service, "result": r})
		except Exception:
			pass
		return {"ok": True, "result": r}
	except Exception as e:
		return {"ok": False, "error": str(e)}

class ReplicateReq(BaseModel):
	agent_id: str

@app.post('/replicate')
async def replicate(req: ReplicateReq, request: Request, actor: str = Depends(get_current_actor)):
	return replicate_agent(req.agent_id)


class ExecuteWasmReq(BaseModel):
	wasm_module: str
	agent_id: str
	metadata: dict | None = None


@app.post('/execute_wasm')
async def execute_wasm(req: ExecuteWasmReq, request: Request, actor: str = Depends(get_current_actor)):
	# wrapper endpoint that gates via SafeGuard, logs and executes via trusted-executor
	res = safe_execute_wasm(req.wasm_module, getattr(request.state, 'actor', req.agent_id), req.metadata)
	return res

if __name__ == '__main__':
	import uvicorn
	uvicorn.run(app, host='0.0.0.0', port=8020)
