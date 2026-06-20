from fastapi import FastAPI
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import httpx
import os

SERVICE_NAME = "resilience_score"
CIRCUIT_URL = "http://circuit_breakers:8700"

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

@app.get("/homeostasis/score")
async def get_score():
    http_requests_total.labels("GET", "/homeostasis/score", 200).inc()
    score = 100.0
    
    # We could fetch all circuit breaker states, but since we don't have an endpoint for ALL states,
    # let's just check orchestrator and executor for now.
    services_to_check = ["orchestrator", "executor_api"]
    
    async with httpx.AsyncClient() as client:
        for svc in services_to_check:
            try:
                res = await client.get(f"{CIRCUIT_URL}/homeostasis/circuit/{svc}", timeout=2.0)
                if res.status_code == 200:
                    state = res.json().get("state")
                    if state == "open":
                        score -= 30.0
                    elif state == "half-open":
                        score -= 10.0
            except Exception:
                # If circuit breaker service is down, resilience takes a big hit
                score -= 50.0
                break
                
    return {"score": max(0.0, score), "status": "healthy" if score > 80 else "degraded"}
