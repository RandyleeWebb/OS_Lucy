from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time

SERVICE_NAME = "circuit_breakers"

app = FastAPI(title=f"Lucy {SERVICE_NAME}")

http_requests_total = Counter(
    f"{SERVICE_NAME}_http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"]
)

# In-memory circuit breaker state
# service_name -> {"failures": 0, "last_failure_time": 0, "state": "closed"}
cb_state = {}

class FailureReport(BaseModel):
    service: str
    error: str

@app.get("/health")
async def health():
    http_requests_total.labels("GET", "/health", 200).inc()
    return {"up": True, "service": SERVICE_NAME, "version": "0.1.0"}

@app.get("/metrics")
async def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

@app.post("/homeostasis/circuit/report")
async def report_failure(req: FailureReport):
    http_requests_total.labels("POST", "/homeostasis/circuit/report", 200).inc()
    now = time.time()
    if req.service not in cb_state:
        cb_state[req.service] = {"failures": 0, "last_failure_time": 0, "state": "closed"}
        
    state = cb_state[req.service]
    state["failures"] += 1
    state["last_failure_time"] = now
    
    # Trip breaker if more than 5 failures
    if state["failures"] >= 5 and state["state"] == "closed":
        state["state"] = "open"
        return {"status": "circuit_tripped", "service": req.service}
        
    return {"status": "recorded", "service": req.service, "state": state["state"]}

@app.get("/homeostasis/circuit/{service}")
async def check_circuit(service: str):
    http_requests_total.labels("GET", "/homeostasis/circuit", 200).inc()
    now = time.time()
    state = cb_state.get(service, {"failures": 0, "last_failure_time": 0, "state": "closed"})
    
    # Auto-recovery logic (half-open) after 30 seconds
    if state["state"] == "open" and (now - state["last_failure_time"] > 30):
        state["state"] = "half-open"
        state["failures"] = 0 # reset to test
        
    return {"service": service, "state": state["state"]}
