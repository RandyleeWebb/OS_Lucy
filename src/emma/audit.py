import os
import json
import time
import asyncio
import logging

from typing import Any, Dict, Optional

logger = logging.getLogger("emma.audit")

# Audit log path
AUDIT_LOG_PATH = os.getenv("TERMINAL_AUDIT_PATH", "/app/data/terminal_audit.log")


def _write_file_line(obj: Dict[str, Any]) -> None:
	try:
		os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
		with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
			f.write(json.dumps(obj) + "\n")
	except Exception as e:
		logger.warning("Failed to write audit line: %s", e)


async def _push_redis(obj: Dict[str, Any]) -> None:
	try:
		# Import redis helper lazily to avoid startup deps
		from bus import _get_redis
		r = await _get_redis()
		if r:
			await r.xadd("audit", {"payload": json.dumps(obj)})
	except Exception as e:
		logger.debug("Failed to push audit to redis: %s", e)


def append_audit(event_type: str, payload: Dict[str, Any], source: Optional[str] = None) -> None:
	obj = {
		"ts": time.time(),
		"type": event_type,
		"source": source,
		"payload": payload,
	}
	# write sync
	_write_file_line(obj)
	# schedule redis push
	try:
		asyncio.create_task(_push_redis(obj))
	except RuntimeError:
		# no running loop - ignore
		pass
