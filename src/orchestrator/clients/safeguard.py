import requests
import os

SAFEGUARD_URL = os.environ.get("SAFEGUARD_URL", "http://safeguard:8013/audit")


def audit(agent_id: str, action: str, metadata: dict | None = None):
	payload = {"agent_id": agent_id, "action": action, "metadata": metadata}
	try:
		r = requests.post(SAFEGUARD_URL, json=payload, timeout=5)
		try:
			return r.json()
		except Exception:
			return {"decision": "deny", "reason": "safeguard_parse_error", "datavault": {"entry_hash": None}}
	except Exception as e:
		return {"decision": "deny", "reason": "safeguard_unreachable"}
