from fastapi import FastAPI
from pydantic import BaseModel, Field
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

SERVICE_NAME = "gravity_model"

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

class GravityRequest(BaseModel):
    action: str
    tool_used: str | None = None
    user_trust_level: str = "standard"  # e.g., guest, standard, admin
    execution_context: str = "default"  # e.g., local, internet-facing

@app.post("/gravity/score")
async def score(req: GravityRequest):
    http_requests_total.labels("POST", "/gravity/score", 200).inc()
    
    base_score = 10.0
    
    # Action sensitivity
    if "system" in req.action:
        base_score += 40.0
    elif "db" in req.action:
        base_score += 30.0
    elif "read" in req.action:
        base_score += 5.0
        
    # Tool risk
    high_risk_tools = ["shell", "eval", "sql_executor", "network_request"]
    if req.tool_used in high_risk_tools:
        base_score += 30.0
        
    # User trust adjustments
    if req.user_trust_level == "guest":
        base_score *= 1.5
    elif req.user_trust_level == "admin":
        base_score *= 0.5
        
    # Execution context adjustments
    if req.execution_context == "internet-facing":
        base_score += 20.0
        
    final_score = min(100.0, max(0.0, base_score))
    
    return {"score": final_score}
