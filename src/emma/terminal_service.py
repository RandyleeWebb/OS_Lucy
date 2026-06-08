import os
import json
import time
import logging
import asyncio
import subprocess
from typing import List, Dict, Any

logger = logging.getLogger("emma.terminal")

# Persistent history path (optional). Directory is created if missing.
HISTORY_PATH = os.getenv("TERMINAL_HISTORY_PATH", "/app/data/terminal_history.json")
HISTORY_MAX = 200


def _append_history(entry: Dict[str, Any]) -> None:
	try:
		os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
		if os.path.exists(HISTORY_PATH):
			try:
				with open(HISTORY_PATH, "r", encoding="utf-8") as f:
					data = json.load(f)
			except Exception:
				data = []
		else:
			data = []

		data.append(entry)
		if len(data) > HISTORY_MAX:
			data = data[-HISTORY_MAX:]

		with open(HISTORY_PATH, "w", encoding="utf-8") as f:
			json.dump(data, f, indent=2)
	except Exception as e:
		logger.warning("Unable to write terminal history: %s", e)


def get_history(limit: int = 50) -> List[Dict[str, Any]]:
	try:
		if not os.path.exists(HISTORY_PATH):
			return []
		with open(HISTORY_PATH, "r", encoding="utf-8") as f:
			data = json.load(f)
		return data[-limit:]
	except Exception as e:
		logger.warning("Unable to read terminal history: %s", e)
		return []


async def execute_command(command: str, shell: bool = True, timeout: int = 60) -> Dict[str, Any]:
	"""Execute a command in a thread, capture stdout/stderr, return exit code.

	Returns a dict with keys: stdout, stderr, exit_code, duration, timestamp, command
	"""
	start = time.time()

	def _run() -> Dict[str, Any]:
		try:
			# Use subprocess.run in a thread to avoid blocking the event loop.
			result = subprocess.run(
				command,
				shell=shell,
				capture_output=True,
				text=True,
				timeout=timeout,
			)
			return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}
		except subprocess.TimeoutExpired as e:
			return {"stdout": e.stdout or "", "stderr": (e.stderr or "") + f"\n[Timeout after {timeout}s]", "exit_code": -124}
		except Exception as e:
			return {"stdout": "", "stderr": str(e), "exit_code": -1}

	# Simple rate-limit: one command per second per process by default
	# NOTE: this is a basic in-process guard; for distributed or stronger limits
	# integrate with Redis or a centralized rate limiter.
	now = time.time()
	if hasattr(execute_command, "_last_run"):
		last = getattr(execute_command, "_last_run")
		if now - last < 1.0:
			return {"timestamp": int(start), "command": command, "shell": shell, "timeout": timeout, "duration": 0.0, "result": {"stdout": "", "stderr": "Rate limit: please wait before issuing commands.", "exit_code": -125}}
	setattr(execute_command, "_last_run", now)

	result = await asyncio.to_thread(_run)
	duration = time.time() - start

	entry = {
		"timestamp": int(start),
		"command": command,
		"shell": bool(shell),
		"timeout": int(timeout),
		"duration": duration,
		"result": result,
	}

	# Persist history best-effort
	try:
		_append_history(entry)
	except Exception:
		logger.exception("Failed to append terminal history")

	logger.info("Executed terminal command: %s (exit=%s, duration=%.2fs)", command, result.get("exit_code"), duration)
	return entry
