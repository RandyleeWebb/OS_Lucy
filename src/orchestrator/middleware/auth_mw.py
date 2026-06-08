from fastapi import Request, HTTPException
import os

# Simple bearer token allowlist or single token
TOKENS = [t for t in os.environ.get('ORCH_API_TOKENS', '').split(',') if t]
SINGLE = os.environ.get('ORCH_API_TOKEN')


def extract_actor_from_token(token: str) -> str:
	# simple mapping: token may be 'service:<name>' or just a token; for MVP we return token as actor
	if token.startswith('service:'):
		return token.split(':', 1)[1]
	return token


def require_auth(headers: dict) -> tuple[bool, dict]:
	# backward-compatible helper used by unit tests
	auth = headers.get('authorization') or headers.get('Authorization')
	if not auth:
		return False, {"status_code": 401, "detail": "missing_authorization"}
	parts = auth.split()
	if len(parts) != 2 or parts[0].lower() != 'bearer':
		return False, {"status_code": 401, "detail": "invalid_authorization_header"}
	token = parts[1]
	# check allowlist
	if SINGLE and token == SINGLE:
		actor = extract_actor_from_token(token)
		return True, {"actor": actor}
	if TOKENS and token in TOKENS:
		actor = extract_actor_from_token(token)
		return True, {"actor": actor}
	return False, {"status_code": 403, "detail": "forbidden_token"}


def get_current_actor(request: Request) -> str:
	"""FastAPI dependency that validates Authorization header and sets request.state.actor."""
	auth = request.headers.get('authorization')
	if not auth:
		raise HTTPException(status_code=401, detail='missing_authorization')
	parts = auth.split()
	if len(parts) != 2 or parts[0].lower() != 'bearer':
		raise HTTPException(status_code=401, detail='invalid_authorization_header')
	token = parts[1]
	if SINGLE and token == SINGLE:
		actor = extract_actor_from_token(token)
		request.state.actor = actor
		return actor
	if TOKENS and token in TOKENS:
		actor = extract_actor_from_token(token)
		request.state.actor = actor
		return actor
	raise HTTPException(status_code=403, detail='forbidden_token')
