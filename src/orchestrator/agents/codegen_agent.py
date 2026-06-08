from ..ollama_client import generate as ollama_generate
from ..clients import safeguard
from ..clients import datavault
import httpx


async def generate_and_run(prompt: str, language: str = 'python'):
	# 1) call ollama to generate code
	code = await ollama_generate(prompt)
	# safest return if code is not a string
	if not isinstance(code, str):
		code = str(code)
	# 2) audit via safeguard (using the orchestrator client function)
	audit = safeguard.audit("codegen", code)
	if audit.get('decision') == 'deny':
		datavault.write('codegen', {'code': code, 'audit': audit})
		return {"ok": False, "reason": "safeguard_denied", "audit": audit}
	# 3) execute via trusted-executor
	try:
		# For safety, require execution as wasm. Assume `code` is a base64-encoded wasm blob
		# and send it to the trusted-executor with lang="wasm".
		async with httpx.AsyncClient(timeout=30) as client:
			resp = await client.post('http://trusted-executor:8040/execute', json={"lang": "wasm", "code": code})
			res = resp.json()
	except Exception as e:
		res = {"ok": False, "error": str(e)}
	# log into datavault
	datavault.write('codegen', {'code': code, 'audit': audit, 'execution': res})
	return {"ok": True, "code": code, "execution": res}


async def compile_and_execute_wasm(prompt: str, agent_id: str):
	# This helper expects Ollama to produce base64 wasm. In practice you'd compile HLL -> wasm here.
	wasm_b64 = await ollama_generate(prompt)
	# ensure it's a string
	if not isinstance(wasm_b64, str):
		wasm_b64 = str(wasm_b64)
	# call orchestrator endpoint via client wrapper
	from ..clients.trusted_executor import safe_execute_wasm
	return safe_execute_wasm(wasm_b64, agent_id, metadata={"origin": "codegen"})


async def generate_and_run_wasm(prompt: str, language: str = 'python'):
	# Generate code via Ollama
	code = await ollama_generate(prompt)
	if not isinstance(code, str):
		code = str(code)
	# Audit
	audit = safeguard.audit("codegen", code)
	if audit.get('decision') == 'deny':
		datavault.write('codegen', {'code': code, 'audit': audit})
		return {"ok": False, "reason": "safeguard_denied", "audit": audit}

	# For now, expect that code is a base64-encoded wasm blob returned by the model
	# In future: compile high-level code to wasm (tooling/compilers required)
	try:
		async with httpx.AsyncClient(timeout=60.0) as client:
			resp = await client.post('http://trusted-executor:8040/execute', json={"lang": "wasm", "code": code})
			res = resp.json()
	except Exception as e:
		res = {"ok": False, "error": str(e)}

	datavault.write('codegen', {'code': code, 'audit': audit, 'execution': res})
	return {"ok": True, "code": code, "execution": res}
