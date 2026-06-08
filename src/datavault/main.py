from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import os
import json
import hmac
import hashlib
from datetime import datetime
from typing import Any, Dict

app = FastAPI()

LOG_PATH = os.environ.get("DATAVAULT_LOG", "/data/datavault.log")
HMAC_KEY = os.environ.get("DATAVAULT_HMAC_KEY", "dev-key")
SIGNING_KEY = os.environ.get("DATAVAULT_SIGNING_KEY", "dev-dv-key")

class LogEntry(BaseModel):
	source: str
	payload: Dict[str, Any]
	timestamp: float | None = None


def compute_hash(data: bytes) -> str:
	return hashlib.sha256(data).hexdigest()


def compute_hmac(data: bytes) -> str:
	return hmac.new(HMAC_KEY.encode(), data, hashlib.sha256).hexdigest()


def compute_signature(data: bytes) -> str:
	# DataVault signing (HMAC-based for now)
	return hmac.new(SIGNING_KEY.encode(), data, hashlib.sha256).hexdigest()


def read_last_hash() -> str | None:
	try:
		with open(LOG_PATH, "rb") as f:
			lines = f.readlines()
			if not lines:
				return None
			last = lines[-1].decode().strip()
			obj = json.loads(last)
			return obj.get("entry_hash")
	except FileNotFoundError:
		return None


@app.post("/log")
async def append_log(entry: LogEntry):
	entry_dict = entry.dict()
	entry_dict["timestamp"] = entry_dict.get("timestamp") or datetime.utcnow().timestamp()
	prev_hash = read_last_hash()
	entry_json = json.dumps({"source": entry_dict["source"], "payload": entry_dict["payload"], "timestamp": entry_dict["timestamp"]}, separators=(",", ":"))
	entry_hash = compute_hash(entry_json.encode())
	record = {
		"prev_hash": prev_hash,
		"entry_hash": entry_hash,
		"hmac": compute_hmac(entry_json.encode()),
		"record": json.loads(entry_json),
	}
	os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
	with open(LOG_PATH, "a", encoding="utf-8") as f:
		f.write(json.dumps(record) + "\n")

	# produce an AuditReceipt signed by DataVault over the canonical entry_hash + prev_hash + timestamp
	timestamp = entry_dict["timestamp"]
	receipt_payload = {"entry_hash": entry_hash, "prev_hash": prev_hash, "timestamp": timestamp}
	receipt_json = json.dumps(receipt_payload, separators=(",", ":"), sort_keys=True)
	signature = compute_signature(receipt_json.encode())
	audit_receipt = {"receipt": receipt_payload, "signature": signature, "signer": "datavault"}

	return {"ok": True, "entry_hash": entry_hash, "audit_receipt": audit_receipt}


@app.get("/verify")
async def verify_chain():
	try:
		with open(LOG_PATH, "r", encoding="utf-8") as f:
			prev = None
			idx = 0
			for line in f:
				idx += 1
				obj = json.loads(line)
				record = obj.get("record")
				entry_json = json.dumps(record, separators=(",", ":"))
				computed_hash = compute_hash(entry_json.encode())
				computed_hmac = compute_hmac(entry_json.encode())
				if obj.get("entry_hash") != computed_hash:
					return {"ok": False, "reason": f"hash mismatch at line {idx}"}
				if obj.get("hmac") != computed_hmac:
					return {"ok": False, "reason": f"hmac mismatch at line {idx}"}
				if obj.get("prev_hash") != prev:
					return {"ok": False, "reason": f"chain link mismatch at line {idx}"}
				prev = obj.get("entry_hash")
		return {"ok": True, "entries_checked": idx}
	except FileNotFoundError:
		return {"ok": True, "entries_checked": 0}


@app.get("/entries")
async def get_entries(source: str | None = None, agent_id: str | None = None, limit: int = 50):
	try:
		with open(LOG_PATH, "r", encoding="utf-8") as f:
			lines = f.readlines()
			res = []
			for line in reversed(lines):
				if len(res) >= limit:
					break
				obj = json.loads(line)
				rec = obj.get("record", {})
				rec_source = rec.get("source")
				payload = rec.get("payload") or {}
				if source and rec_source != source:
					continue
				if agent_id:
					# support nested payload.agent_id or payload.get('agent_id')
					pid = payload.get("agent_id") if isinstance(payload, dict) else None
					if pid != agent_id:
						continue
				res.append({"prev_hash": obj.get("prev_hash"), "entry_hash": obj.get("entry_hash"), "hmac": obj.get("hmac"), "record": rec})
			return {"ok": True, "count": len(res), "entries": res}
	except FileNotFoundError:
		return {"ok": True, "count": 0, "entries": []}


@app.get("/health")
async def health():
	return {"status": "ok", "service": "datavault"}


if __name__ == '__main__':
	import uvicorn
	uvicorn.run(app, host="0.0.0.0", port=8012)
