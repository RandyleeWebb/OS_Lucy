import json
import fnmatch
from pathlib import Path
from typing import List, Dict, Any

# ----------------------------------------------------------------------
# Load the capability schema (once) – defines the allowed actions
# ----------------------------------------------------------------------
SCHEMA_PATH = Path(__file__).parent / "capabilities_schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text())

# ----------------------------------------------------------------------
# Helper: load an agent's profile (JSON) from ``profiles/<agent>.json``
# ----------------------------------------------------------------------
PROFILES_DIR = Path(__file__).parent / "profiles"

def _load_profile(agent_name: str) -> Dict[str, Any]:
    profile_path = PROFILES_DIR / f"{agent_name}.json"
    if not profile_path.is_file():
        raise FileNotFoundError(f"Capability profile for '{agent_name}' not found at {profile_path}")
    return json.loads(profile_path.read_text())

# ----------------------------------------------------------------------
# Protected‑path matcher – immutable infrastructure files
# ----------------------------------------------------------------------
PROTECTED_GLOBS: List[str] = [
    "/app/docker-compose.yml",
    "/app/**/Dockerfile",
    "/app/proxy/**",
    "/app/secret/**",
    "/app/src/capability_manager/capabilities_schema.json",
    "/app/src/llm_gateway/**",
    "/app/src/emma/**",
]

def is_protected_path(path: str) -> bool:
    """Return True if *path* matches any protected glob.

    The function works with absolute container‑internal paths (the
    ``/app`` prefix is used throughout the Docker images).
    """
    normalized = Path(path).as_posix()
    return any(fnmatch.fnmatch(normalized, glob) for glob in PROTECTED_GLOBS)

# ----------------------------------------------------------------------
# Core authorisation check
# ----------------------------------------------------------------------
def authorize(
    agent_name: str,
    action: str,
    target_path: str | None = None,
    allow_network: bool | None = None,
) -> bool:
    """Validate that *agent_name* may perform *action*.

    Parameters
    ----------
    agent_name:
        Name of the calling agent (e.g. ``"self_extension"``).
    action:
        One of the actions listed in the capability schema.
    target_path:
        Absolute path the action operates on (if applicable).
    allow_network:
        For actions that may open network sockets – defaults to the
        value defined in the profile.
    """
    profile = _load_profile(agent_name)
    capabilities = profile.get("capabilities", [])

    # Find a matching capability entry
    for cap in capabilities:
        if cap.get("action") != action:
            continue
        # ------------------------------------------------------------------
        # Path‑based check – only applied when a ``resource_pattern`` is set
        # ------------------------------------------------------------------
        if target_path is not None:
            pattern = cap.get("resource_pattern")
            if not fnmatch.fnmatch(target_path, pattern):
                continue
        # ------------------------------------------------------------------
        # Network permission – only relevant for ``call_llm`` (or any
        # future network‑capable action).
        # ------------------------------------------------------------------
        if allow_network is not None:
            if cap.get("allow_network", False) != allow_network:
                continue
        # ------------------------------------------------------------------
        # If we get here the capability matches.
        # ------------------------------------------------------------------
        # Extra safety: block any write to a protected path.
        if action in {"write_file", "replace_file_content", "multi_replace_file_content"} and target_path:
            if is_protected_path(target_path):
                raise PermissionError(f"Attempt to modify protected path: {target_path}")
        return True

    # No matching capability – reject
    raise PermissionError(f"Agent '{agent_name}' is not authorized for action '{action}' on '{target_path}'")

# ----------------------------------------------------------------------
# Convenience wrappers used by other services
# ----------------------------------------------------------------------
def can_read(agent: str, path: str) -> bool:
    return authorize(agent, "read_file", target_path=path)

def can_write(agent: str, path: str) -> bool:
    return authorize(agent, "write_file", target_path=path)

def can_call_llm(agent: str, host_allowed: bool = True) -> bool:
    return authorize(agent, "call_llm", allow_network=host_allowed)

# ----------------------------------------------------------------------
# Example usage (removed in production)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # Simple sanity check – run with ``python -m capability_manager.guard``
    try:
        print("Self‑Extension can write to /app/src/self_extension/main.py?",
              can_write("self_extension", "/app/src/self_extension/main.py"))
    except PermissionError as e:
        print("DENIED:", e)
