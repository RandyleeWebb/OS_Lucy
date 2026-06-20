Key generation and JWKS trust registry

Usage (local):

python3 scripts/keygen.py

This writes keys to build/keys/ with sg.json, dv.json, orch.json and jwks_combined.json.

CI Integration:
- Run scripts/keygen.py in CI job
- Upload jwks_combined.json as an artifact or pass its contents to services via mounted file/env
- Set SAFEGUARD_PRIV_KEY, DATAVAULT_PRIV_KEY, ORCH_PRIV_KEY (hex) for services and SAFEGUARD_PUB_KEY, DATAVAULT_PUB_KEY, ORCH_PUB_KEY for verification services, or mount jwks file and have services fetch /.well-known/jwks.json

Notes:
- Keys are emitted in hex for convenience; jwks x values are base64url values.
