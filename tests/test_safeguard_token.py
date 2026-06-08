from src.orchestrator.middleware.safeguard_middleware import verify_signature
import json, hmac, hashlib, os


def test_verify_signature_roundtrip():
	os.environ['SAFEGUARD_HMAC_KEY'] = 'test-key'
	payload = {"agent_id": "a1", "action": "execute_wasm", "decision": "allow", "timestamp": 12345}
	token_json = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode()
	sig = hmac.new(os.environ['SAFEGUARD_HMAC_KEY'].encode(), token_json, hashlib.sha256).hexdigest()
	token = {"token": payload, "signature": sig}
	assert verify_signature(token) is True
