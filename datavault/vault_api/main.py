from fastapi import FastAPI, HTTPException, Request
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import httpx

SERVICE_NAME = "vault_api"
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

@app.post("/vault/append")
async def append(request: Request):
    http_requests_total.labels("POST", "/vault/append", 200).inc()
    body = await request.json()
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{LEDGER_URL}/vault/append", json=body)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=500, detail=f"Ledger error: {str(exc)}")

@app.get("/vault/entry/{seq_id}")
async def get_entry(seq_id: int):
    http_requests_total.labels("GET", "/vault/entry", 200).inc()
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{LEDGER_URL}/vault/entry/{seq_id}")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=500, detail=f"Ledger error: {str(exc)}")
