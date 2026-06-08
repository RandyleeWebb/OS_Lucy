from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi import WebSocket, WebSocketDisconnect
from engine import EmmaEngine
from validator import verify_secret
from pydantic import BaseModel
from terminal_sessions import manager as session_manager
from datetime import datetime
from bus import publish, _get_redis, subscribe
import asyncio
from skit_pipeline import process_skit

app = FastAPI(title="EMMA Evolution Gatekeeper")
engine = EmmaEngine()


@app.get("/health")
async def health():
    """Basic health endpoint used by orchestration and local checks.

    Returns service status, Redis connectivity, and a quick pending proposals count.
    """
    # Check Redis availability
    try:
        redis = await _get_redis()
        redis_ok = bool(redis)
    except Exception:
        redis_ok = False

    # Get a quick pending proposals count without blocking the event loop
    try:
        pending = await asyncio.to_thread(engine._count_pending_proposals_sync)
    except Exception:
        pending = None

    status = {
        "status": "ok",
        "redis": redis_ok,
        "pending_proposals": pending,
    }
    return status


@app.post("/terminal/session")
async def create_session(authorized: bool = Depends(verify_secret)):
    sess = session_manager.create()
    return {"session_id": sess.id}


@app.post("/terminal/session/{session_id}/close")
async def close_session(session_id: str, authorized: bool = Depends(verify_secret)):
    ok = session_manager.close(session_id)
    return {"closed": ok}


@app.websocket("/terminal/ws/{session_id}")
async def terminal_ws(websocket: WebSocket, session_id: str):
    # Note: FastAPI WebSockets do not support header dependencies well; expecting the secret as a query param
    await websocket.accept()
    try:
        session = session_manager.get(session_id)
        if not session:
            await websocket.send_text("[error] session not found")
            await websocket.close()
            return

        # Consumer task: forward queue entries to websocket
        async def consumer():
            while True:
                data = await session.queue.get()
                await websocket.send_text(data)

        consumer_task = asyncio.create_task(consumer())

        # Producer loop: receive input from client and write to pty
        try:
            while True:
                msg = await websocket.receive_text()
                # Allow client to send JSON { type: 'input', data: '<keystrokes>' }
                try:
                    import json
                    parsed = json.loads(msg)
                    if isinstance(parsed, dict) and parsed.get('type') == 'input' and 'data' in parsed:
                        session.write(parsed['data'])
                    else:
                        # fallback: write raw string
                        session.write(msg)
                except Exception:
                    session.write(msg)
        except WebSocketDisconnect:
            pass
        finally:
            consumer_task.cancel()
            await websocket.close()

    except Exception as e:
        await websocket.send_text(f"[error] {e}")
        await websocket.close()

@app.on_event("startup")
async def startup():
    # Start the periodic heartbeat after the event loop is running
    await engine.start_heartbeat()

@app.on_event("startup")
async def start_skit_listener():
    asyncio.create_task(event_listener())

async def event_listener():
    async for event in subscribe("skit:generate"):
        try:
            await process_skit(event)
        except Exception as e:
            # publish failure event
            await publish("skit:failed", {"error": str(e), "payload": event})
            raise

@app.post("/notify")
async def receive(event: dict, authorized: bool = Depends(verify_secret)):
    """Endpoint for Lucy (Self‑Extension Engine) to push events.
    Expected keys: `event` (str) and `payload` (dict).
    """
    await engine.handle_event(event.get("event"), event.get("payload", {}))
    return {"status": "received"}

@app.post("/skit/generate")
async def generate_skit(request: dict, authorized: bool = Depends(verify_secret)):
    """Generate a multi‑speaker skit.
    Enforces a simple rate‑limit of 20 skits per hour using Redis.
    Publishes a `skit:generate` event for downstream processing.
    """
    # Rate limiting
    now = datetime.utcnow()
    key = f"skit:rate:{now:%Y%m%d%H}"
    redis = await _get_redis()
    if not redis:
        # Redis isn't available yet — return a 503 so callers can retry
        raise HTTPException(status_code=503, detail="Redis unavailable, try again later")

    count = await redis.incr(key)
    if count == 1:
        # set expiry of 1 hour for the key
        await redis.expire(key, 3600)
    if count > 20:
        raise HTTPException(status_code=429, detail="Rate limit exceeded: 20 skits per hour")

    # Publish event for pipeline processing
    await publish("skit:generate", request)
    return {"status": "queued", "rate_count": count}

class CommandRequest(BaseModel):
    proposal_id: int | None = None

@app.post("/command/{cmd}")
async def command(cmd: str, body: CommandRequest, authorized: bool = Depends(verify_secret)):
    """Accept a command from the UI and forward it to Lucy via the neuro‑bus.
    Supported `cmd` values: `request_explanation`, `request_risk_analysis`,
    `request_diff_summary`, `request_sandbox_logs`.
    """
    await engine.send_command(cmd, body.proposal_id)
    return {"command": cmd, "status": "sent"}


class ShellRequest(BaseModel):
    command: str
    timeout: int | None = 60


@app.post("/terminal/exec")
async def terminal_exec(req: ShellRequest, authorized: bool = Depends(verify_secret)):
    """Execute a shell command via Emma's terminal service.

    Returns stdout/stderr/exit_code and stores the entry in history.
    """
    entry = await engine.run_shell(req.command, timeout=(req.timeout or 60))
    return entry


@app.get("/terminal/history")
async def terminal_history(limit: int = 50, authorized: bool = Depends(verify_secret)):
    return await engine.terminal_history(limit)
