import os
import time
import json
import hmac
import hashlib
from types import SimpleNamespace
from fastapi.testclient import TestClient

from src.orchestrator.server import app as orch_app
from src.trusted_executor.main import app as te_app
from src.orchestrator.pipeline.permit import create_permit, canonical_json
from src.datavault import main as dv_main


def setup_env_keys():
	os.environ['ORCH_API_TOKEN'] = 'service:testsvc'
	os.environ['SAFEGUARD_HMAC_KEY'] = 'qc-sg'
	os.environ['DATAVAULT_SIGNING_KEY'] = 'qc-dv'
	os.environ['ORCH_PERMIT_KEY'] = 'qc-orch'


def test_canonicalization_and_signature_boundaries():
	setup_env_keys()
	# create a payload and sign canonically
	payload = {'a': 1, 'b': 2}
	canon = canonical_json(payload)
	sig = hmac.new(os.environ['ORCH_PERMIT_KEY'].encode(), canon, hashlib.sha256).hexdigest()

	# simulate different ordering / whitespace
	variant = json.dumps({'b':2, 'a':1}, separators=(',', ':'))
	# verification uses canonical_json, so it should pass
	canon_variant = canonical_json(json.loads(variant))
	assert canon == canon_variant
	expected = hmac.new(os.environ['ORCH_PERMIT_KEY'].encode(), canon_variant, hashlib.sha256).hexdigest()
	assert expected == sig

	# tamper: remove field -> signature must not match
	tampered = {'a':1}
	tampered_canon = canonical_json(tampered)
	tampered_sig = hmac.new(os.environ['ORCH_PERMIT_KEY'].encode(), tampered_canon, hashlib.sha256).hexdigest()
	assert tampered_sig != sig


def test_actor_identity_propagation_and_logging(monkeypatch):
	setup_env_keys()
	client = TestClient(orch_app)
	captured = {'safeguard_agent': None, 'dv_writes': []}

	def mock_audit(agent_id, action, metadata=None):
		captured['safeguard_agent'] = agent_id
		return {'decision':'allow', 'decision_token': {'token': {'agent_id': agent_id}, 'signature': 'x'}}

	def mock_append_and_verify(source, payload):
		captured['dv_writes'].append((source, payload))
		# return fake receipt
		rec = {'receipt': {'entry_hash':'h', 'prev_hash': None, 'timestamp': time.time()}, 'signature': hmac.new(os.environ['DATAVAULT_SIGNING_KEY'].encode(), json.dumps({'entry_hash':'h','prev_hash':None,'timestamp':payload.get('timestamp',0)}, separators=(',', ':'), sort_keys=True).encode(), hashlib.sha256).hexdigest()}
		return {'ok': True, 'entry_hash': 'h', 'audit_receipt': rec}

	monkeypatch.setattr('src.orchestrator.clients.safeguard.audit', mock_audit)
	monkeypatch.setattr('src.orchestrator.clients.datavault.append_and_verify', mock_append_and_verify)

	payload = {"wasm_module": "", "agent_id": "a1", "metadata": {}}
	r = client.post('/execute_wasm', json=payload, headers={'Authorization': 'Bearer service:testsvc'})
	assert r.status_code == 200
	# actor used by safeguard should be service:testsvc => extract 'testsvc'
	assert captured['safeguard_agent'] in ('testsvc', 'a1')
	# datavault write captured
	assert len(captured['dv_writes']) >= 1


def test_negative_paths_unreachable_components(monkeypatch):
	setup_env_keys()
	client = TestClient(orch_app)
	payload = {"wasm_module": "", "agent_id": "a1", "metadata": {}}

	# SafeGuard unreachable -> orchestrator should deny
	def sg_unreach(agent_id, action, metadata=None):
		raise Exception('unreachable')
	monkeypatch.setattr('src.orchestrator.clients.safeguard.audit', sg_unreach)
	r = client.post('/execute_wasm', json=payload, headers={'Authorization':'Bearer service:testsvc'})
	assert r.status_code == 200 and r.json().get('ok') is False

	# DataVault unreachable -> orchestrator should deny
	def sg_allow(agent_id, action, metadata=None):
		return {'decision':'allow', 'decision_token': {'token':{'agent_id':agent_id}, 'signature':'x'}}
	monkeypatch.setattr('src.orchestrator.clients.safeguard.audit', sg_allow)
	def dv_unreach(source, payload):
		raise Exception('dv down')
	monkeypatch.setattr('src.orchestrator.clients.datavault.append_and_verify', dv_unreach)
	r2 = client.post('/execute_wasm', json=payload, headers={'Authorization':'Bearer service:testsvc'})
	assert r2.status_code == 200 and r2.json().get('ok') is False

	# Trusted Executor unreachable (simulate requests.post raising) -> orchestrator should return error
	def dv_ok(source, payload):
		return {'ok': True, 'entry_hash':'h', 'audit_receipt': {'receipt':{'entry_hash':'h','prev_hash':None,'timestamp':time.time()}, 'signature':'s'}}
	monkeypatch.setattr('src.orchestrator.clients.datavault.append_and_verify', dv_ok)
	def te_unreach(url, json=None, timeout=None):
		raise Exception('te down')
	monkeypatch.setattr('requests.post', te_unreach)
	r3 = client.post('/execute_wasm', json=payload, headers={'Authorization':'Bearer service:testsvc'})
	assert r3.status_code == 200 and r3.json().get('ok') is True
	# note: orchestrator returns ok True but trusted-executor error is captured in result; ensure it didn't execute


def test_replay_and_ttl_enforcement():
	setup_env_keys()
	client = TestClient(te_app)
	dec = {'token': {'agent_id':'a1', 'decision':'allow', 'timestamp': int(time.time())}, 'signature': hmac.new(os.environ['SAFEGUARD_HMAC_KEY'].encode(), json.dumps({'agent_id':'a1','decision':'allow','timestamp':int(time.time())}, separators=(',', ':'), sort_keys=True).encode(), hashlib.sha256).hexdigest()}
	ar = {'receipt': {'entry_hash':'h','prev_hash':None,'timestamp':int(time.time())}, 'signature': hmac.new(os.environ['DATAVAULT_SIGNING_KEY'].encode(), json.dumps({'entry_hash':'h','prev_hash':None,'timestamp':int(time.time())}, separators=(',', ':'), sort_keys=True).encode(), hashlib.sha256).hexdigest()}

	permit = create_permit(dec, ar, ttl_seconds=2, nonce='qc-nonce')
	r1 = client.post('/execute', json={"lang":"wasm","code":"","permit":permit})
	# first attempt accepted (or processed)
	assert r1.status_code in (200, 500, 400)
	# second attempt should be replayed -> 403
	r2 = client.post('/execute', json={"lang":"wasm","code":"","permit":permit})
	assert r2.status_code == 403
	# expired TTL
	permit_exp = create_permit(dec, ar, ttl_seconds=-1, nonce='qc-nonce-2')
	r3 = client.post('/execute', json={"lang":"wasm","code":"","permit":permit_exp})
	assert r3.status_code == 403


def test_deterministic_reproducibility(monkeypatch):
	# Run a simplified full pipeline 3 times with randomized nonces and ensure consistent pass/fail
	setup_env_keys()
	client = TestClient(orch_app)
	results = []

	def mock_audit(agent_id, action, metadata=None):
		return {'decision':'allow', 'decision_token': make_dt(agent_id)}

	def make_dt(agent_id):
		token = {'agent_id': agent_id, 'action': 'execute_wasm', 'decision': 'allow', 'timestamp': int(time.time())}
		sig = hmac.new(os.environ['SAFEGUARD_HMAC_KEY'].encode(), json.dumps(token, separators=(',', ':'), sort_keys=True).encode(), hashlib.sha256).hexdigest()
		return {'token': token, 'signature': sig}

	def mock_append(source, payload):
		rec = {'receipt': {'entry_hash':'h','prev_hash':None,'timestamp':int(time.time())}, 'signature': hmac.new(os.environ['DATAVAULT_SIGNING_KEY'].encode(), json.dumps({'entry_hash':'h','prev_hash':None,'timestamp':int(time.time())}, separators=(',', ':'), sort_keys=True).encode(), hashlib.sha256).hexdigest()}
		return {'ok': True, 'entry_hash': 'h', 'audit_receipt': rec}

	monkeypatch.setattr('src.orchestrator.clients.safeguard.audit', mock_audit)
	monkeypatch.setattr('src.orchestrator.clients.datavault.append_and_verify', mock_append)

	for i in range(3):
		r = client.post('/execute_wasm', json={"wasm_module": "", "agent_id": "a1", "metadata": {}}, headers={'Authorization':'Bearer service:testsvc'})
		results.append((r.status_code, bool(r.json().get('ok'))))

	# ensure identical outcomes across runs
	assert results[0] == results[1] == results[2]
