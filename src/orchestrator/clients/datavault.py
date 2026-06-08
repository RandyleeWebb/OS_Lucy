import requests
import os
import json
import hmac
import hashlib

DATAVAULT_URL = os.environ.get("DATAVAULT_URL", "http://datavault:8012/log")
DATAVAULT_SIGNING_KEY = os.environ.get("DATAVAULT_SIGNING_KEY", "dev-dv-key")

def write(source: str, payload: dict):
	try:
		r = requests.post(DATAVAULT_URL, json={"source": source, "payload": payload}, timeout=5)
		try:
			return r.json()
		except Exception:
			return {"ok": True, "entry_hash": None}
	except Exception as e:
		return {"ok": False, "reason": str(e)}


def append_log(source: str, payload: dict):
	# convenience alias
	return write(source, payload)


def verify_receipt(receipt: dict) -> bool:
	if not receipt or not isinstance(receipt, dict):
		return False
	sig = receipt.get('signature')
	payload = receipt.get('receipt')
	if not sig or not payload:
		return False
	canonical = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode()
	expected = hmac.new(DATAVAULT_SIGNING_KEY.encode(), canonical, hashlib.sha256).hexdigest()
	return hmac.compare_digest(expected, sig)


def append_and_verify(source: str, payload: dict, timeout: int = 5):
	try:
		r = requests.post(DATAVAULT_URL, json={"source": source, "payload": payload}, timeout=timeout)
		r.raise_for_status()
		data = r.json()
	except Exception as e:
		return {"ok": False, "reason": "datavault_unreachable", "error": str(e)}

	receipt = data.get('audit_receipt')
	if not receipt:
		return {"ok": False, "reason": "no_audit_receipt", "response": data}

	if not verify_receipt(receipt):
		return {"ok": False, "reason": "invalid_receipt_signature", "receipt": receipt}

	return {"ok": True, "entry_hash": data.get('entry_hash'), "audit_receipt": receipt}


def safe_write_with_cb(cb, source: str, payload: dict):
	"""Attempt to write using a circuit breaker or fallback to local noop."""
	try:
		return cb.call(lambda: write(source, payload), fallback=lambda e: {"ok": False, "reason": str(e)})
	except Exception as e:
		return {"ok": False, "reason": str(e)}
