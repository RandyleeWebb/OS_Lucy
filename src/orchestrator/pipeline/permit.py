import os
import json
import time
import hmac
import hashlib
import uuid

ORCH_PERMIT_KEY = os.environ.get('ORCH_PERMIT_KEY', 'dev-orch-key')


def canonical_json(obj: dict) -> bytes:
	return json.dumps(obj, separators=(',', ':'), sort_keys=True).encode()


def create_permit(decision_token: dict, audit_receipt: dict, ttl_seconds: int = 60, nonce: str | None = None) -> dict:
	if nonce is None:
		nonce = uuid.uuid4().hex
	expires_at = int(time.time()) + int(ttl_seconds)
	payload = {
		'decision_token': decision_token,
		'audit_receipt': audit_receipt,
		'nonce': nonce,
		'ttl': expires_at,
	}
	canon = canonical_json(payload)
	signature = hmac.new(ORCH_PERMIT_KEY.encode(), canon, hashlib.sha256).hexdigest()
	permit = {'payload': payload, 'signature': signature, 'signer': 'orchestrator'}
	return permit
