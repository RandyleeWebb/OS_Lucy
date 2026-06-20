from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

SERVICE_NAME = "datavault"

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

class StubRequest(BaseModel):
    payload: dict | None = None

@app.post(f"/{SERVICE_NAME}/stub")
async def stub(req: StubRequest):
    http_requests_total.labels("POST", f"/{SERVICE_NAME}/stub", 200).inc()
    return {"status": "ok", "service": SERVICE_NAME, "payload": req.payload}
