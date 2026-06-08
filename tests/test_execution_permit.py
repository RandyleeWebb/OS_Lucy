import os
import time
import json
import hmac, hashlib
from src.orchestrator.pipeline.permit import create_permit, canonical_json


def test_execution_permit_sign_verify_valid():
	os.environ['ORCH_PERMIT_KEY'] = 'test-orch'
	os.environ['SAFEGUARD_HMAC_KEY'] = 'test-sg'
	os.environ['DATAVAULT_SIGNING_KEY'] = 'test-dv'
	decision = {'token': {'agent_id': 'a1', 'decision': 'allow', 'timestamp': 1}, 'signature': hmac.new(os.environ['SAFEGUARD_HMAC_KEY'].encode(), json.dumps({'agent_id': 'a1', 'decision': 'allow', 'timestamp': 1}, separators=(',', ':'), sort_keys=True).encode(), hashlib.sha256).hexdigest()}
	audit = {'receipt': {'entry_hash': 'x', 'prev_hash': None, 'timestamp': 1}, 'signature': hmac.new(os.environ['DATAVAULT_SIGNING_KEY'].encode(), json.dumps({'entry_hash': 'x', 'prev_hash': None, 'timestamp': 1}, separators=(',', ':'), sort_keys=True).encode(), hashlib.sha256).hexdigest()}
	permit = create_permit(decision, audit, ttl_seconds=60, nonce='n1')
	canon = canonical_json(permit['payload'])
	sig = hmac.new(os.environ['ORCH_PERMIT_KEY'].encode(), canon, hashlib.sha256).hexdigest()
	assert sig == permit['signature']


def test_execution_permit_expired_ttl():
	os.environ['ORCH_PERMIT_KEY'] = 'test-orch'
	dec = {'token': {}, 'signature': 's'}
	ar = {'receipt': {}, 'signature': 's'}
	permit = create_permit(dec, ar, ttl_seconds= -1, nonce='n2')
	assert int(time.time()) > permit['payload']['ttl']


def test_execution_permit_replay_nonce():
	os.environ['ORCH_PERMIT_KEY'] = 'test-orch'
	dec = {'token': {}, 'signature': 's'}
	ar = {'receipt': {}, 'signature': 's'}
	p1 = create_permit(dec, ar, ttl_seconds=60, nonce='replay1')
	p2 = create_permit(dec, ar, ttl_seconds=60, nonce='replay1')
	assert p1['payload']['nonce'] == p2['payload']['nonce']
