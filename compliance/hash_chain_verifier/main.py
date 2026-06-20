from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import httpx
import hashlib
import json

SERVICE_NAME = "hash_chain_verifier"
LEDGER_URL = "http://ledger:8600"

app = FastAPI(title=f"Lucy {SERVICE_NAME}")

http_requests_total = Counter(
    f"{SERVICE_NAME}_http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"]
)

@app.get("/health")
async def health():
    http_requests_total.labels("GET", "/health", 200).inc()
    return {"up": True, "service": SERVICE_NAME, "version": "0.1.0"}

@app.get("/metrics")
async def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

@app.post("/verify")
async def verify():
    http_requests_total.labels("POST", "/verify", 200).inc()
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{LEDGER_URL}/vault/entries?limit=10000")
            resp.raise_for_status()
            entry_stubs = resp.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=500, detail=f"Ledger unreachable: {str(exc)}")
            
    if not entry_stubs:
        return {"ok": True, "message": "Ledger is empty"}
        
    async with httpx.AsyncClient() as client:
        expected_prev_hash = "0" * 64
        for stub in entry_stubs:
            seq_id = stub["sequence_id"]
            
            try:
                row_resp = await client.get(f"{LEDGER_URL}/vault/entry/{seq_id}")
                row_resp.raise_for_status()
                row = row_resp.json()
            except httpx.HTTPError as exc:
                return {"ok": False, "error": f"Failed to fetch entry {seq_id}: {str(exc)}"}
                
            # Verify chain linkage
            if row["prev_hash"] != expected_prev_hash:
                return {"ok": False, "error": f"Chain broken at sequence {seq_id}. Expected prev_hash {expected_prev_hash}, got {row['prev_hash']}"}
                
            # Verify cryptographic hash
            entry_dict = {
                "intent_id": row["intent_id"],
                "timestamp": row["timestamp"],
                "actor": row["actor"],
                "intent_hash": row["intent_hash"],
                "safeguard_decision": row["safeguard_decision"],
                "execution_metrics": row["execution_metrics"],
                "signature": row["signature"],
                "prev_hash": row["prev_hash"]
            }
            data_string = json.dumps(entry_dict, sort_keys=True)
            computed_hash = hashlib.sha256(data_string.encode('utf-8')).hexdigest()
            
            if computed_hash != row["curr_hash"]:
                return {"ok": False, "error": f"Hash mismatch at sequence {seq_id}. Computed {computed_hash}, stored {row['curr_hash']}"}
                
            expected_prev_hash = row["curr_hash"]
            
    return {"ok": True, "verified_entries": len(entry_stubs)}
