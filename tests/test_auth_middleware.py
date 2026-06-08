import os
from src.orchestrator.middleware.auth_mw import require_auth, get_current_actor
from types import SimpleNamespace


def test_auth_middleware_no_token_unauthorized():
	ok, info = require_auth({})
	assert not ok
	assert info.get('status_code') == 401


def test_auth_middleware_invalid_token_forbidden():
	os.environ['ORCH_API_TOKEN'] = 'good'
	ok, info = require_auth({'authorization': 'Bearer bad'})
	assert not ok
	assert info.get('status_code') == 403


def test_auth_middleware_valid_token_passes_and_sets_actor():
	os.environ['ORCH_API_TOKEN'] = 'service:svc1'
	ok, info = require_auth({'authorization': 'Bearer service:svc1'})
	assert ok
	assert info.get('actor') == 'svc1'
	# test dependency behavior
	req = SimpleNamespace(headers={'authorization': 'Bearer service:svc1'}, state=SimpleNamespace())
	actor = get_current_actor(req)
	assert actor == 'svc1'
