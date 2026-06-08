import os
import requests
import json

SAFEGUARD_URL = os.environ.get('SAFEGUARD_URL', 'http://safeguard:8013/audit')


def verify_signature(token: dict) -> bool:
	# basic HMAC verify using SAFEGUARD_HMAC_KEY env on orchestrator side for tests
	key = os.environ.get('SAFEGUARD_HMAC_KEY', 'dev-sg-key')
	sig = token.get('signature')
	payload = token.get('token')
	if not sig or not payload:
		return False
	import hmac, hashlib
	canonical = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode()
	expected = hmac.new(key.encode(), canonical, hashlib.sha256).hexdigest()
	return hmac.compare_digest(expected, sig)


def verify_safeguard_decision(agent_id: str, action: str, metadata: dict | None = None) -> dict:
	# call safeguard service to obtain decision and decision_token, verify signature
	try:
		r = requests.post(SAFEGUARD_URL, json={"agent_id": agent_id, "action": action, "metadata": metadata}, timeout=5)
		data = r.json()
	except Exception as e:
		return {"ok": False, "reason": "safeguard_unreachable", "error": str(e)}

	# expect decision_token in response
	token = data.get('decision_token')
	if not token:
		return {"ok": False, "reason": "no_decision_token", "safeguard": data}

	if not verify_signature(token):
		return {"ok": False, "reason": "invalid_token_signature", "safeguard": data}

	decision = data.get('decision')
	if decision != 'allow':
		return {"ok": False, "reason": "deny", "safeguard": data}

	return {"ok": True, "decision_token": token}
