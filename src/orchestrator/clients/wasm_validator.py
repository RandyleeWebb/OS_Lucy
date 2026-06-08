import base64
from typing import Dict, Any


def read_uleb128(data: bytes, idx: int) -> (int, int):
	"""Read unsigned LEB128 starting at idx; return (value, new_index)"""
	result = 0
	shift = 0
	pos = idx
	while pos < len(data):
		byte = data[pos]
		result |= (byte & 0x7F) << shift
		pos += 1
		if (byte & 0x80) == 0:
			break
		shift += 7
	return result, pos


def validate_wasm_base64(wasm_b64: str) -> Dict[str, Any]:
	"""Validate base64-encoded WASM module; return metadata dict.

	Returns: { valid:bool, reason:str, size:int, exports:int, memories:int }
	"""
	try:
		data = base64.b64decode(wasm_b64)
	except Exception as e:
		return {"valid": False, "reason": f"base64_decode_error: {e}", "size": 0, "exports": 0, "memories": 0}

	size = len(data)
	# minimal wasm header
	if size < 8 or data[0:4] != b"\x00asm":
		return {"valid": False, "reason": "invalid_magic", "size": size, "exports": 0, "memories": 0}

	# skip magic and version
	idx = 8
	exports = 0
	memories = 0
	# iterate sections
	while idx < size:
		sec_id = data[idx]
		idx += 1
		sec_size, idx = read_uleb128(data, idx)
		sec_start = idx
		sec_end = sec_start + sec_size
		if sec_end > size:
			break
		if sec_id == 7:  # export section
			# read vector count
			count, p = read_uleb128(data, sec_start)
			exports = count
		if sec_id == 5:  # memory section
			count, p = read_uleb128(data, sec_start)
			memories = count
		idx = sec_end

	# basic memory estimate: check memory section limits if present (not parsing limits deeply)
	# try to parse memory limits (very shallow): if memory section present, set estimated_mb to 16MB per memory
	estimated_memory_mb = 0
	if memories > 0:
		estimated_memory_mb = memories * 16
	return {"valid": True, "reason": "ok", "size": size, "exports": exports, "memories": memories, "estimated_memory_mb": estimated_memory_mb}
