from fastapi import FastAPI
from pydantic import BaseModel
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import redis.asyncio as redis
import os

SERVICE_NAME = "chaos_injector"
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

app = FastAPI(title=f"Lucy {SERVICE_NAME}")

http_requests_total = Counter(
    f"{SERVICE_NAME}_http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"]
)

# Connect to Redis
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

@app.get("/health")
async def health():
    http_requests_total.labels("GET", "/health", 200).inc()
    return {"up": True, "service": SERVICE_NAME, "version": "0.1.0"}

@app.get("/metrics")
async def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

class ChaosReq(BaseModel):
    target_service: str
    mode: str  # e.g., "latency", "drop", "error", "off"
    intensity: float = 1.0 # 0.0 to 1.0, e.g. 0.5 = 50% drop rate

@app.post("/homeostasis/chaos")
async def chaos(req: ChaosReq):
    http_requests_total.labels("POST", "/homeostasis/chaos", 200).inc()
    key = f"chaos:{req.target_service}"
    if req.mode == "off":
        await redis_client.delete(key)
        return {"status": "chaos_disabled", "target": req.target_service}
    else:
        payload = {"mode": req.mode, "intensity": req.intensity}
        import json
        await redis_client.set(key, json.dumps(payload))
        return {"status": "chaos_enabled", "target": req.target_service, "config": payload}
