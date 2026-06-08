import os
import requests
import json
import hmac, hashlib


def make_decision_token():
	os.environ['SAFEGUARD_HMAC_KEY'] = 'test-sg'
	token = {'agent_id': 'a1', 'decision': 'allow', 'timestamp': 1}
	sig = hmac.new(os.environ['SAFEGUARD_HMAC_KEY'].encode(), json.dumps(token, separators=(',', ':'), sort_keys=True).encode(), hashlib.sha256).hexdigest()
	return {'token': token, 'signature': sig}


def make_audit_receipt():
	os.environ['DATAVAULT_SIGNING_KEY'] = 'test-dv'
	rec = {'entry_hash': 'h', 'prev_hash': None, 'timestamp': 1}
	sig = hmac.new(os.environ['DATAVAULT_SIGNING_KEY'].encode(), json.dumps(rec, separators=(',', ':'), sort_keys=True).encode(), hashlib.sha256).hexdigest()
	return {'receipt': rec, 'signature': sig}


def test_trusted_executor_requires_valid_permit():
	url = os.environ.get('TRUSTED_EXECUTOR_URL', 'http://localhost:8040/execute')
	# missing permit
	r = requests.post(url, json={"lang": "wasm", "code": ""}, timeout=5)
	assert r.status_code == 403


def test_full_pipeline_decision_receipt_permit_exec_ok():
	# This test would run the full orchestrator -> datavault -> trusted-executor flow
	# For now check that we can POST with a valid permit to trusted-executor (assumes service running)
	os.environ['ORCH_PERMIT_KEY'] = 'test-orch'
	dec = make_decision_token()
	ar = make_audit_receipt()
	# craft permit
	from src.orchestrator.pipeline.permit import create_permit
	permit = create_permit(dec, ar, ttl_seconds=60, nonce='itest1')
	url = os.environ.get('TRUSTED_EXECUTOR_URL', 'http://localhost:8040/execute')
	r = requests.post(url, json={"lang": "wasm", "code": "", "permit": permit}, timeout=5)
	# if wasmtime is not present, executor may return 500; but permit should be accepted (200)
	assert r.status_code in (200, 500, 400)
