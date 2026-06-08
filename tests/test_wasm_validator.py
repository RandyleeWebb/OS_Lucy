import base64
from orchestrator.clients.wasm_validator import validate_wasm_base64

# minimal wasm module (wasm header + version, empty)
minimal = b"\x00asm" + (1).to_bytes(4, 'little')
minimal_b64 = base64.b64encode(minimal).decode()

def test_minimal_wasm():
	meta = validate_wasm_base64(minimal_b64)
	assert meta['valid'] == True
	assert meta['size'] >= 8

