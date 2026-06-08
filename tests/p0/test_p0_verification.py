import os
import json
import base64
import time
import hmac
import hashlib
from types import SimpleNamespace
from fastapi.testclient import TestClient

from src.orchestrator.server import app as orch_app
from src.trusted_executor.main import app as te_app
from src.orchestrator.pipeline.permit import create_permit, canonical_json


def setup_keys():
	os.environ['ORCH_API_TOKEN'] = 'service:testsvc'
	os.environ['SAFEGUARD_HMAC_KEY'] = 'test-sg'
	os.environ['DATAVAULT_SIGNING_KEY'] = 'test-dv'
	os.environ['ORCH_PERMIT_KEY'] = 'test-orch'


def make_decision_token():
	token = {'agent_id': 'a1', 'action': 'execute_wasm', 'decision': 'allow', 'timestamp': int(time.time())}
	sig = hmac.new(os.environ['SAFEGUARD_HMAC_KEY'].encode(), json.dumps(token, separators=(',', ':'), sort_keys=True).encode(), hashlib.sha256).hexdigest()
	return {'token': token, 'signature': sig}


def make_audit_receipt():
	rec = {'entry_hash': 'h1', 'prev_hash': None, 'timestamp': int(time.time())}
	sig = hmac.new(os.environ['DATAVAULT_SIGNING_KEY'].encode(), json.dumps(rec, separators=(',', ':'), sort_keys=True).encode(), hashlib.sha256).hexdigest()
	return {'receipt': rec, 'signature': sig}


def test_auth_layer():
	setup_keys()
	client = TestClient(orch_app)
	payload = {"wasm_module": "", "agent_id": "a1", "metadata": {}}

	# No token -> 401
	r = client.post('/execute_wasm', json=payload)
	assert r.status_code == 401

	# Invalid token -> 403
	r = client.post('/execute_wasm', json=payload, headers={'Authorization': 'Bearer bad'})
	assert r.status_code == 403

	# Valid token -> reaches SafeGuard (we'll monkeypatch SafeGuard in other tests)
	r = client.post('/execute_wasm', json=payload, headers={'Authorization': f"Bearer {os.environ['ORCH_API_TOKEN']}"})
	# since SafeGuard/Datavault may block, we only assert not 401/403
	assert r.status_code not in (401, 403)


def test_safeguard_enforcement_and_datavault_receipt(monkeypatch):
	setup_keys()
	client = TestClient(orch_app)
	payload = {"wasm_module": "dGVzdA==", "agent_id": "a1", "metadata": {}}

	# Mock SafeGuard to deny
	def mock_audit_deny(agent_id, action, metadata=None):
		return {"decision": "deny", "reason": "test_deny"}

	monkeypatch.setattr('src.orchestrator.clients.safeguard.audit', mock_audit_deny)
	r = client.post('/execute_wasm', json=payload, headers={'Authorization': f"Bearer {os.environ['ORCH_API_TOKEN']}"})
	assert r.status_code == 200
	assert r.json().get('ok') is False
	assert r.json().get('reason') == 'safeguard_denied'

	# Mock SafeGuard allow and Datavault failure cases
	def mock_audit_allow(agent_id, action, metadata=None):
		return {"decision": "allow", "decision_token": make_decision_token()}

	monkeypatch.setattr('src.orchestrator.clients.safeguard.audit', mock_audit_allow)

	# Datavault returns non-200 / malformed receipt
	def mock_append_bad(source, payload):
		return {"ok": False, "reason": "datavault_unreachable"}

	monkeypatch.setattr('src.orchestrator.clients.datavault.append_and_verify', mock_append_bad)
	r = client.post('/execute_wasm', json=payload, headers={'Authorization': f"Bearer {os.environ['ORCH_API_TOKEN']}"})
	assert r.status_code == 200
	assert r.json().get('ok') is False
	assert r.json().get('reason') == 'datavault_receipt_required'

	# Datavault returns malformed receipt
	def mock_append_malformed(source, payload):
		return {"ok": False, "reason": "no_audit_receipt"}

	monkeypatch.setattr('src.orchestrator.clients.datavault.append_and_verify', mock_append_malformed)
	r = client.post('/execute_wasm', json=payload, headers={'Authorization': f"Bearer {os.environ['ORCH_API_TOKEN']}"})
	assert r.json().get('ok') is False

	# Datavault returns valid receipt -> orchestrator should create permit and call trusted-executor
	audit = make_audit_receipt()
	def mock_append_ok(source, payload):
		return {"ok": True, "entry_hash": "h1", "audit_receipt": audit}

	captured = {}

	def fake_post(url, json=None, timeout=None):
		# capture the body passed to trusted-executor
		captured['body'] = json
		return SimpleNamespace(status_code=200, json=lambda: {"ok": True, "executed": False})

	monkeypatch.setattr('src.orchestrator.clients.datavault.append_and_verify', mock_append_ok)
	monkeypatch.setattr('requests.post', fake_post)

	r = client.post('/execute_wasm', json=payload, headers={'Authorization': f"Bearer {os.environ['ORCH_API_TOKEN']}"})
	assert r.json().get('ok') is True
	# ensure permit present and has required fields
	body = captured.get('body')
	assert body and 'permit' in body
	permit = body['permit']
	payload = permit.get('payload')
	assert 'decision_token' in payload and 'audit_receipt' in payload and 'nonce' in payload and 'ttl' in payload
	# verify orchestrator signature
	canon = canonical_json(permit['payload'])
	expected = hmac.new(os.environ['ORCH_PERMIT_KEY'].encode(), canon, hashlib.sha256).hexdigest()
	assert expected == permit['signature']


def test_trusted_executor_permit_verification():
	setup_keys()
	client = TestClient(te_app)

	# missing permit -> 403
	r = client.post('/execute', json={"lang": "wasm", "code": ""})
	assert r.status_code == 403

	# tampered permit -> invalid signature
	dec = make_decision_token()
	ar = make_audit_receipt()
	permit = create_permit(dec, ar, ttl_seconds=60, nonce='n-test')
	# tamper signature
	permit_bad = dict(permit)
	permit_bad['signature'] = 'bad'
	r = client.post('/execute', json={"lang": "wasm", "code": "", "permit": permit_bad})
	assert r.status_code == 403

	# expired ttl
	permit_exp = create_permit(dec, ar, ttl_seconds=-1, nonce='n-exp')
	r = client.post('/execute', json={"lang": "wasm", "code": "", "permit": permit_exp})
	assert r.status_code == 403

	# valid permit -> may return 500 if wasmtime missing, but should not be 403
	permit_ok = create_permit(dec, ar, ttl_seconds=60, nonce='n-ok')
	r = client.post('/execute', json={"lang": "wasm", "code": "", "permit": permit_ok})
	assert r.status_code in (200, 500, 400)

	# replay nonce: reuse permit_ok nonce should be rejected on second attempt
	r2 = client.post('/execute', json={"lang": "wasm", "code": "", "permit": permit_ok})
	assert r2.status_code == 403


def test_negative_path_datavault_kill(monkeypatch):
	setup_keys()
	client = TestClient(orch_app)
	payload = {"wasm_module": "dGVzdA==", "agent_id": "a1", "metadata": {}}

	# SafeGuard allows
	def mock_audit_allow(agent_id, action, metadata=None):
		return {"decision": "allow", "decision_token": make_decision_token()}
	monkeypatch.setattr('src.orchestrator.clients.safeguard.audit', mock_audit_allow)

	# Datavault dies mid-flow (simulate exception)
	def mock_append_exc(source, payload):
		raise Exception('datavault_down')
	monkeypatch.setattr('src.orchestrator.clients.datavault.append_and_verify', mock_append_exc)

	r = client.post('/execute_wasm', json=payload, headers={'Authorization': f"Bearer {os.environ['ORCH_API_TOKEN']}"})
	# orchestrator should abort and not proceed to allow execution
	assert r.status_code == 200
	assert r.json().get('ok') is False
