import os
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, validator
import httpx
from typing import List, Optional, Dict, Any

app = FastAPI(title="Lucy Planner")

# Shared secret – reuse same env var as Tool Registry
SHARED_SECRET = os.getenv("TOOL_REGISTRY_SECRET", "lucy-secret")

def verify_secret(x_secret_key: str = Header(...)):
    if x_secret_key != SHARED_SECRET:
        raise HTTPException(status_code=401, detail="Invalid secret")
    return True

# --- Request/Response models ---
class GoalRequest(BaseModel):
    goal: str
    context: Optional[dict] = None

HEAVY_CAPABILITIES = {"generate_song", "long_tts", "full_mix"}

# Global in‑memory store for plugin capabilities
PLUGIN_CAPABILITIES: Dict[str, Dict[str, Any]] = {}

class PlanStep(BaseModel):
    tool: str
    endpoint: str
    payload: Optional[dict] = None
    description: Optional[str] = None
    heavy: bool = False

class PlanResponse(BaseModel):
    steps: List[PlanStep]
    notes: Optional[List[str]] = None

# --- Helper functions ---
async def fetch_tools() -> List[dict]:
    async with httpx.AsyncClient() as client:
        r = await client.get("http://tool_registry:8005/tools")
        r.raise_for_status()
        return r.json()

def interpret_goal_llm(goal: str) -> List[str]:
    """Placeholder LLM – map keywords to capabilities."""
    mapping = {
        "skit": "generate_skit",
        "song": "generate_song",
        "mix": "mix",
        "stream": "stream",
        "audio": "stream",
    }
    caps = []
    for word, cap in mapping.items():
        if word in goal.lower():
            caps.append(cap)
    return caps

def match_capability_to_tool(cap_name: str, tools: List[dict]) -> dict:
    for t in tools:
        if cap_name in t.get("capabilities", []):
            return t
    raise ValueError(f"No registered tool provides capability '{cap_name}'")

@app.on_event("startup")
async def load_plugin_capabilities():
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get("http://tool_registry:8005/plugins", params={"status": "approved"})
            r.raise_for_status()
        except Exception as e:
            print(f"Failed to load plugins on startup: {e}")
            return
        plugins = r.json()

    for p in plugins:
        for cap in p["capabilities"]:
            PLUGIN_CAPABILITIES[cap["name"]] = {
                "plugin_id": p["id"],
                "entrypoint": p.get("entrypoint", {}),
                "method": cap.get("method"),
                "path": cap.get("path"),
                "input_schema": cap.get("input_schema"),
                "output_schema": cap.get("output_schema"),
            }

# New step model for plugin calls
class PluginCallStep(BaseModel):
    type: str = "plugin_call"
    capability: str
    plugin_id: str
    args: dict

@app.post("/plan", response_model=PlanResponse, dependencies=[Depends(verify_secret)])
async def create_plan(request: GoalRequest):
    capabilities = interpret_goal_llm(request.goal)
    if not capabilities:
        raise HTTPException(status_code=400, detail="Could not extract any capabilities from goal")
    tools = await fetch_tools()
    steps: List[PlanStep] = []
    notes: List[str] = []
    for cap in capabilities:
        # First, check if this is a plugin capability
        if cap in PLUGIN_CAPABILITIES:
            plugin = PLUGIN_CAPABILITIES[cap]
            steps.append(
                PluginCallStep(
                    capability=cap,
                    plugin_id=plugin["plugin_id"],
                    args={"goal": request.goal, "capability": cap}
                )
            )
        else:
            try:
                tool = match_capability_to_tool(cap, tools)
                endpoint = f"{tool['base_url']}/{cap}"
                payload = {"goal": request.goal, "capability": cap}
                steps.append(
                    PlanStep(
                        tool=tool["name"],
                        endpoint=endpoint,
                        payload=payload,
                        description=f"Execute '{cap}' via {tool['name']}",
                        heavy=cap in HEAVY_CAPABILITIES,
                    )
                )
            except Exception as e:
                notes.append(str(e))
    if not steps:
        raise HTTPException(status_code=400, detail="No tools could be matched for extracted capabilities")
    return PlanResponse(steps=steps, notes=notes or None)
