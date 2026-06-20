from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import json
import os
import httpx

SERVICE_NAME = "policy_engine"
POLICY_PATH = os.path.join(os.path.dirname(__file__), "policy.json")

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

class EvalRequest(BaseModel):
    intent_id: str
    action: str
    parameters: dict = Field(default_factory=dict)
    timestamp: str
    metadata: dict = Field(default_factory=dict)

def load_policy():
    if os.path.exists(POLICY_PATH):
        with open(POLICY_PATH, "r") as f:
            return json.load(f)
    return {
        "max_tokens": 4096,
        "forbidden_tools": [],
        "forbidden_hosts": [],
        "forbidden_actions": []
    }

@app.post("/safeguard/eval")
async def evaluate(req: EvalRequest):
    http_requests_total.labels("POST", "/safeguard/eval", 200).inc()
    reasons = []
    permitted = True
    
    # Load DSL
    policy = load_policy()
    
    # 1. Check basic DSL rules
    if req.action in policy.get("forbidden_actions", []):
        reasons.append(f"Action '{req.action}' is forbidden by policy DSL.")
        permitted = False
        
    tool_used = req.parameters.get("tool")
    if tool_used in policy.get("forbidden_tools", []):
        reasons.append(f"Tool '{tool_used}' is forbidden by policy DSL.")
        permitted = False

    host = req.parameters.get("host")
    if host:
        # Simplistic wildcard match
        for forbidden in policy.get("forbidden_hosts", []):
            if forbidden.endswith("*") and host.startswith(forbidden[:-1]):
                reasons.append(f"Host '{host}' matches forbidden pattern '{forbidden}'.")
                permitted = False
            elif host == forbidden:
                reasons.append(f"Host '{host}' is explicitly forbidden.")
                permitted = False

    # 2. Check AST (if code is provided)
    code = req.parameters.get("code")
    if code:
        async with httpx.AsyncClient() as client:
            try:
                ast_res = await client.post("http://ast_validator:8501/ast/validate", json={"code": code})
                if ast_res.status_code == 200:
                    ast_data = ast_res.json()
                    if not ast_data.get("valid", True):
                        permitted = False
                        reasons.extend(ast_data.get("reasons", []))
            except Exception as e:
                # Fail closed on AST service error
                permitted = False
                reasons.append(f"AST Validator unreachable or failed: {str(e)}")

    # 3. Calculate Gravity Score
    gravity_score = 0.0
    async with httpx.AsyncClient() as client:
        try:
            grav_req = {
                "action": req.action,
                "tool_used": tool_used,
                "user_trust_level": req.metadata.get("user_trust_level", "standard"),
                "execution_context": req.metadata.get("execution_context", "default")
            }
            grav_res = await client.post("http://gravity_model:8503/gravity/score", json=grav_req)
            if grav_res.status_code == 200:
                gravity_score = grav_res.json().get("score", 0.0)
            else:
                # Fallback penalty if gravity service fails
                gravity_score = 100.0
                reasons.append("Gravity Model failed, assuming maximum risk.")
        except Exception as e:
            gravity_score = 100.0
            reasons.append(f"Gravity Model unreachable: {str(e)}")

    # Reject if gravity is too high
    if gravity_score > 80.0:
        permitted = False
        reasons.append(f"Gravity score ({gravity_score}) exceeds acceptable risk threshold.")

    return {"permitted": permitted, "gravity": gravity_score, "reasons": reasons}
