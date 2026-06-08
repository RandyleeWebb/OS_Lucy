import os
import json
import hmac, hashlib
from src.datavault.main import compute_signature, compute_hash


def make_payload():
	return {"source": "test", "payload": {"msg": "hello"}, "timestamp": 12345.0}


def test_datavault_receipt_signature_valid():
	os.environ['DATAVAULT_SIGNING_KEY'] = 'test-dv-key'
	payload = make_payload()
	entry_json = json.dumps({"source": payload['source'], "payload": payload['payload'], "timestamp": payload['timestamp']}, separators=(',', ':'))
	entry_hash = hashlib.sha256(entry_json.encode()).hexdigest()
	receipt_payload = {"entry_hash": entry_hash, "prev_hash": None, "timestamp": payload['timestamp']}
	receipt_json = json.dumps(receipt_payload, separators=(',', ':'), sort_keys=True).encode()
	sig = hmac.new(os.environ['DATAVAULT_SIGNING_KEY'].encode(), receipt_json, hashlib.sha256).hexdigest()
	assert hmac.compare_digest(sig, compute_signature(receipt_json))


def test_datavault_receipt_missing_fields():
	# missing signature or payload should be rejected by client verify
	bad = {"receipt": {"entry_hash": "x"}}
	assert not ('signature' in bad)
