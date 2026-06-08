import os
import json
import asyncio
from bus import publish
from terminal_service import execute_command, get_history
from audit import append_audit

class EmmaEngine:
    def __init__(self):
        self._heartbeat_task = None

    async def start_heartbeat(self):
        async def _beat():
            while True:
                count = await asyncio.to_thread(self._count_pending_proposals_sync)
                await publish("heartbeat", {
                    "cognitive_state": "monitoring",
                    "evolution_state": "idle",
                    "pending_proposals": count,
                    "sandbox_health": "ok",
                })
                await asyncio.sleep(30)
        self._heartbeat_task = asyncio.create_task(_beat())

    async def handle_event(self, event_type: str, payload: dict):
        await publish("emma_event", {"type": event_type, "payload": payload})
        if event_type == "proposal_created":
            await self.send_command("request_diff_summary", payload.get("id"))

    async def send_command(self, cmd: str, proposal_id: int | None = None):
        data = {"command": cmd}
        if proposal_id is not None:
            data["proposal_id"] = proposal_id
        await publish("emma_to_lucy", data)

    async def run_shell(self, command: str, timeout: int = 60):
        """Run a shell command via the terminal service and publish results."""
        entry = await execute_command(command, shell=True, timeout=timeout)
        # Publish a terminal:executed event so other components (UI/logging) can observe
        await publish("terminal:executed", {"command": command, "entry": entry})
        # Audit log
        append_audit("terminal.executed", {"command": command, "entry": entry}, source="emma")
        return entry

    async def terminal_history(self, limit: int = 50):
        return get_history(limit)

    def _count_pending_proposals_sync(self) -> int:
        import sqlite3
        db_path = os.getenv("SELF_EXT_DB", "/app/data/self_extension.db")
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM proposals WHERE status='pending'")
            count = cur.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0  # DB may not exist yet on first boot
