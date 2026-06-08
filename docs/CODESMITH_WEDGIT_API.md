CodeSmith Wedgit API Contract

Request schema (POST /orchestrator/execute_wasm)

{
  "wasm_module": "<base64 wasm bytes>",
  "agent_id": "agent-123",
  "metadata": {"source": "codegen", "description": "..."}
}

Response schema

{
  "ok": true,
  "request_log": {"ok": true, "entry_hash": "..."},
  "result": {"request_id": "...", "ok": true, "exit_code": 0, "stdout": "...", "stderr": "..."},
  "result_log": {"ok": true, "entry_hash": "..."},
  "audit": { ... }
}

Error states
- safeguard_denied: {ok:false, reason:"safeguard_denied", audit: {...}}
- trusted_executor_unavailable: {ok:false, error: "..."}
- invalid_wasm: 400 response

Visual states for UI
- pending: request submitted, awaiting SafeGuard
- denied: SafeGuard denied execution
- allowed: SafeGuard allowed, executing
- executed: execution complete (show stdout/stderr)
