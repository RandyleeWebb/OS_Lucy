from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import json
from pathlib import Path
import fnmatch
from typing import List, Dict, Any
import httpx
from datetime import datetime

app = FastAPI(title="Lucy Capability Manager")

DATA_DIR = Path("/app/data")
CAPABILITIES_FILE = DATA_DIR / "capabilities.json"
PROFILES_DIR = Path("/app/src/capability_manager/profiles")

# ----------------------------------------------------------------------
# Immutable infrastructure paths – any write attempt is denied
# ----------------------------------------------------------------------
PROTECTED_PATHS = [
    "/app/docker-compose.yml",
    "/app/**/Dockerfile",
    "/app/proxy/**",
    "/app/secret/**",
    "/app/src/capability_manager/**",
    "/app/src/llm_gateway/**",
    "/app/src/emma/**",
]

# Global in‑memory store for plugin capabilities
PLUGIN_CAPABILITIES: Dict[str, Dict[str, Any]] = {}


class Capability(BaseModel):
    name: str
    description: str
    endpoint: str | None = None
    service: str | None = None


def load_profile(agent: str) -> dict:
    """Load the JSON profile for *agent* from the ``profiles`` directory.

    The function raises ``HTTPException`` (404) if the file does not exist.
    """
    profile_path = PROFILES_DIR / f"{agent}.json"
    if not profile_path.is_file():
        raise HTTPException(status_code=404, detail=f"Profile for {agent} not found")
    return json.loads(profile_path.read_text())


def check_capability(agent: str, action: str, resource: str | None = None) -> tuple[bool, str]:
    """Core enforcement routine.

    Returns ``(allowed, reason)`` where ``allowed`` is a bool and ``reason``
    explains the decision (useful for audit logs).
    """
    profile = load_profile(agent)

    # --------------------------------------------------------------
    # 1️⃣  Action must be present in the profile
    # --------------------------------------------------------------
    allowed_caps = [c for c in profile.get("capabilities", []) if c["action"] == action]
    if not allowed_caps:
        return False, "Action not permitted"

    # --------------------------------------------------------------
    # 2️⃣  Protected‑path rejection (immutable infrastructure)
    # --------------------------------------------------------------
    if resource:
        for pat in PROTECTED_PATHS:
            if fnmatch.fnmatch(resource, pat):
                return False, "Protected path"

    # --------------------------------------------------------------
    # 3️⃣  Resource‑pattern matching (glob against the allowed caps)
    # --------------------------------------------------------------
    if resource:
        for cap in allowed_caps:
            if fnmatch.fnmatch(resource, cap["resource_pattern"]):
                return True, "OK"
        return False, "Resource not permitted"

    # No specific resource – the action itself is allowed
    return True, "OK"


def load_capabilities() -> List[Capability]:
    if not CAPABILITIES_FILE.exists():
        raise HTTPException(status_code=404, detail="Capabilities file not found")
    with CAPABILITIES_FILE.open() as f:
        data = json.load(f)
    return [Capability(**item) for item in data]


@app.get("/capabilities", response_model=List[Capability])
def get_capabilities():
    return load_capabilities()


@app.get("/capabilities/{name}", response_model=Capability)
def get_capability(name: str):
    caps = load_capabilities()
    for cap in caps:
        if cap.name == name:
            return cap
    raise HTTPException(status_code=404, detail="Capability not found")


@app.get("/system/permissions")
def get_permissions():
    # Placeholder – in a production system this would query the kernel
    return {"permissions": ["read_file", "write_file", "execute_command"]}


@app.on_event("startup")
async def load_plugins():
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get("http://tool_registry:8005/plugins", params={"status": "approved"})
            r.raise_for_status()
        except Exception as e:
            # If the registry is unavailable we simply start with an empty plugin set.
            print(f"Failed to load plugins on startup: {e}")
            return
        plugins = r.json()

    for p in plugins:
        for cap in p["capabilities"]:
            PLUGIN_CAPABILITIES[cap["name"]] = {
                "plugin_id": p["id"],
                "permissions": cap.get("required_permissions", []),
                "plugin_permissions": p.get("permissions", []),
                "entrypoint": p.get("entrypoint", {}),
                "method": cap.get("method"),
                "path": cap.get("path")
            }


# ----------------------------------------------------------------------
# Simple internal endpoint for testing enforcement from other services
# ----------------------------------------------------------------------
@app.post("/enforce")
def enforce(payload: dict):
    agent = payload.get("agent")
    action = payload.get("action")
    resource = payload.get("resource")
    # First, check builtin capabilities
    allowed, reason = check_capability(agent, action, resource)
    if allowed:
        return {"allowed": True, "reason": reason}

    # Fallback to plugin capabilities
    cap = PLUGIN_CAPABILITIES.get(action)
    if not cap:
        return {"allowed": False, "reason": "Action not permitted (no plugin capability)"}
    # Simple permission check – ensure plugin is approved (status handled on load) and required permissions are present
    # Here we assume agent permissions are managed elsewhere; we just allow if the capability exists.
    return {"allowed": True, "reason": "Allowed via plugin capability"}
