import requests
import os
from .datavault import write, append_and_verify
from .safeguard import audit
from .wasm_validator import validate_wasm_base64
from ..pipeline.permit import create_permit

TRUSTED_EXECUTOR_URL = os.environ.get("TRUSTED_EXECUTOR_URL", "http://trusted-executor:8040/execute")


def safe_execute_wasm(wasm_b64: str, agent_id: str, metadata: dict | None = None, timeout: int = 30):
	payload_meta = metadata or {}
	# include wasm size in metadata for audit
	try:
		wasm_size = len(wasm_b64.encode('utf-8'))
	except Exception:
		wasm_size = 0
	payload_meta["wasm_b64_size"] = wasm_size

	# validate wasm
	try:
		meta = validate_wasm_base64(wasm_b64)
	except Exception:
		meta = {"valid": False}
	payload_meta.update({"wasm_validator": meta})

	if not meta.get("valid"):
		dv = write('orchestrator', {'event': 'wasm_validation_failed', 'agent_id': agent_id, 'meta': meta})
		return {"ok": False, "reason": "wasm_invalid", "meta": meta, "datavault": dv}

	# Ask SafeGuard for permission
	# Ask SafeGuard for permission (no-op refresh)
	sg = audit(agent_id, "execute_wasm", payload_meta)
	if sg.get("decision") != "allow":
		dv = write('orchestrator', {'event': 'wasm_execution_denied', 'agent_id': agent_id, 'audit': sg})
		return {"ok": False, "reason": "safeguard_denied", "audit": sg, "datavault": dv}

	# record request in datavault
	# require DataVault to append and return a verified AuditReceipt before proceeding
	req_log = append_and_verify('orchestrator', {'event': 'wasm_execution_request', 'agent_id': agent_id, 'meta': payload_meta})
	if not req_log.get('ok'):
		# abort if datavault did not provide a valid receipt
		return {"ok": False, "reason": "datavault_receipt_required", "datavault": req_log}

	# create ExecutionPermit and pass to trusted-executor
	try:
		decision_token = sg.get('decision_token')
	except Exception:
		decision_token = None

	permit = create_permit(decision_token, req_log.get('audit_receipt'), ttl_seconds=60)

	# call trusted-executor with permit
	try:
		r = requests.post(TRUSTED_EXECUTOR_URL, json={"lang": "wasm", "code": wasm_b64, "timeout": timeout, "permit": permit}, timeout=timeout + 5)
		try:
			res = r.json()
		except Exception:
			res = {"ok": False, "error": "trusted_executor_response_parse_error", "text": r.text}
	except Exception as e:
		res = {"ok": False, "error": str(e)}

	# log result
	res_log = write('orchestrator', {'event': 'wasm_execution_result', 'agent_id': agent_id, 'request_log': req_log, 'result': res})

	return {"ok": True, "request_log": req_log, "result": res, "result_log": res_log, "audit": sg}
