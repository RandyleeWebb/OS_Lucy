#!/usr/bin/env python3
"""
Simple keygen for Ed25519 keys and JWKS output for local/CI use.
Generates keys for safeguard, datavault, orchestrator and a combined jwks.json.
"""
import json
import os
from nacl.signing import SigningKey
import base64

OUT_DIR = os.environ.get('KEYOUT', 'build/keys')
os.makedirs(OUT_DIR, exist_ok=True)

def b64url(b: bytes) -> str:
	return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

def gen(kid_prefix: str):
	sk = SigningKey.generate()
	pk = sk.verify_key
	priv_hex = sk.encode().hex()
	pub_hex = pk.encode().hex()
	kid = f"{kid_prefix}-{os.environ.get('KEY_ID','2026-06')}"
	jwk = {
		"kid": kid,
		"kty": "OKP",
		"crv": "Ed25519",
		"x": b64url(pk.encode())
	}
	out = {
		"kid": kid,
		"private_key_hex": priv_hex,
		"public_key_hex": pub_hex,
		"alg": "Ed25519",
		"jwk": jwk,
	}
	return out

names = ["sg", "dv", "orch", "te"]
all_keys = {}
jwks = {"keys": []}
for n in names:
	o = gen(n)
	fname = os.path.join(OUT_DIR, f"{n}.json")
	with open(fname, 'w') as f:
		json.dump(o, f, indent=2)
	all_keys[n] = o
	jwks['keys'].append(o['jwk'])

combined_path = os.path.join(OUT_DIR, 'jwks_combined.json')
with open(combined_path, 'w') as f:
	json.dump(jwks, f, indent=2)

print(f"Wrote keys to {OUT_DIR}")
print(json.dumps({k:v['kid'] for k,v in all_keys.items()}, indent=2))
