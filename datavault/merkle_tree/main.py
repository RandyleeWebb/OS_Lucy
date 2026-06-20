from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import httpx
import hashlib

SERVICE_NAME = "merkle_tree"
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

def build_merkle_root(leaves: list[str]) -> str:
    if not leaves:
        return ""
    if len(leaves) == 1:
        return leaves[0]
    
    next_level = []
    for i in range(0, len(leaves), 2):
        left = leaves[i]
        right = leaves[i+1] if i+1 < len(leaves) else left
        combined = left + right
        next_level.append(hashlib.sha256(combined.encode('utf-8')).hexdigest())
        
    return build_merkle_root(next_level)

@app.get("/merkle/root")
async def get_root():
    http_requests_total.labels("GET", "/merkle/root", 200).inc()
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{LEDGER_URL}/vault/entries?limit=10000")
            resp.raise_for_status()
            entries = resp.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=500, detail=f"Ledger error: {str(exc)}")
            
    hashes = [e["curr_hash"] for e in entries]
    root = build_merkle_root(hashes)
    return {"root": root, "leaves_count": len(hashes)}
