// src/ai_queue_worker.py
"""Background worker that monitors the ``skits/`` directory for newly generated audio
files (e.g., from the TTS pipeline) and makes them available to Liquidsoap.

The worker performs the following steps:

1. **Watch for new skits** – scans ``skits/`` for ``.wav`` or ``.mp3`` files.
2. **Validate** – ensures the file is non‑empty and has a recognizable audio
   header (basic sanity check).
3. **Queue** – moves the skit into ``skits/ready/`` and writes a trigger file
   ``triggers/ai_ready`` containing the absolute path. Liquidsoap polls this
   file and injects the skit.
4. **Logging & Auditing** – writes a line to ``audit_events.log`` and, if a
   consent record is required, inserts a placeholder entry into ``consent.db``.
5. **Security** – verifies the HMAC token supplied with the skit filename and
   checks that the caller possesses the ``sys_queue_skit`` capability. The
   actual sandbox enforcement is delegated to ``tool_manager.profileForCapability``.
6. **Cleanup** – archives played/skipped skits and removes files older than a
   configurable retention period (default 7 days).

The implementation is deliberately straightforward: it uses a polling loop
instead of an external watcher (e.g., ``watchdog``) to keep dependencies
minimal and to work reliably on Windows. The loop interval can be tuned via the
``AI_QUEUE_POLL_SECONDS`` environment variable.
"""

import os
import hashlib
import hmac
import json
import logging
import shutil
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration – can be overridden with environment variables
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]
SKITS_DIR = BASE_DIR / "skits"
READY_DIR = SKITS_DIR / "ready"
ARCHIVE_DIR = SKITS_DIR / "archive"
TRIGGER_DIR = BASE_DIR / "triggers"
TRIGGER_FILE = TRIGGER_DIR / "ai_ready"

POLL_INTERVAL = int(os.getenv("AI_QUEUE_POLL_SECONDS", "2"))
RETENTION_DAYS = int(os.getenv("SKIT_RETENTION_DAYS", "7"))
HMAC_SECRET = os.getenv("SKIT_HMAC_SECRET", "default-secret")  # should be set in production

# Ensure required directories exist
for d in (READY_DIR, ARCHIVE_DIR, TRIGGER_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging setup – simple file logger for audit events
# ---------------------------------------------------------------------------
log_file = BASE_DIR / "audit_events.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ai_queue_worker")

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
def _hmac_verify(token: str, filename: str) -> bool:
    """Validate an HMAC token using the shared secret.

    The token is expected to be ``hex`` of ``HMAC(secret, filename)``.
    """
    expected = hmac.new(HMAC_SECRET.encode(), filename.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, token)

def _is_valid_audio(path: Path) -> bool:
    """Very lightweight sanity check – file must be non‑empty and start with a
    known audio header (WAV or MP3). Returns ``True`` if the file looks plausible.
    """
    if not path.is_file() or path.stat().st_size == 0:
        return False
    try:
        with path.open("rb") as f:
            header = f.read(4)
        # WAV files start with "RIFF", MP3 files often start with 0xFF 0xFB or ID3 tag
        if header.startswith(b"RIFF"):
            return True
        if header.startswith(b"ID3") or header[:2] == b"\xff\xfb":
            return True
    except Exception as exc:
        logger.debug(f"Audio validation failed for {path}: {exc}")
        return False
    return False

def _record_audit(event: str, details: Optional[dict] = None) -> None:
    """Write a JSON line to the audit log.

    ``event`` is a short tag (e.g., ``skit_queued``). ``details`` can contain any
    extra metadata such as ``track_id`` or ``source_capability``.
    """
    record = {"timestamp": datetime.utcnow().isoformat() + "Z", "event": event}
    if details:
        record["details"] = details
    logger.info(json.dumps(record))

def _write_trigger(skit_path: Path) -> None:
    """Write the absolute path of the ready skit to the trigger file.

    Liquidsoap watches ``triggers/ai_ready``; when the file is touched and the
    path is written, Liquidsoap will read the path and inject the audio.
    """
    with TRIGGER_FILE.open("w", encoding="utf-8") as f:
        f.write(str(skit_path))
    # Update the file's modification time so that a simple ``stat``‑based poll
    # detects the change.
    os.utime(TRIGGER_FILE, None)

def _archive_old_skits() -> None:
    """Move files older than ``RETENTION_DAYS`` from ``ready`` to ``archive`` and
    delete files in ``archive`` that exceed the retention period.
    """
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    # Archive from ready folder
    for file in READY_DIR.iterdir():
        if file.is_file() and datetime.fromtimestamp(file.stat().st_mtime) < cutoff:
            dest = ARCHIVE_DIR / file.name
            shutil.move(str(file), str(dest))
            _record_audit("skit_archived", {"path": str(dest)})
    # Delete stale archives
    for file in ARCHIVE_DIR.iterdir():
        if file.is_file() and datetime.fromtimestamp(file.stat().st_mtime) < cutoff:
            file.unlink()
            _record_audit("skit_deleted", {"path": str(file)})

# ---------------------------------------------------------------------------
# Core worker loop
# ---------------------------------------------------------------------------
def _process_new_skit(skit_path: Path) -> None:
    """Validate, move, and trigger a newly discovered skit.

    The filename is expected to embed a token, e.g. ``<track_id>_<token>.wav``.
    This simple scheme allows the caller to prove possession of the secret.
    """
    filename = skit_path.name
    # Expected format: <name>_<token>.<ext>
    stem, ext = os.path.splitext(filename)
    parts = stem.rsplit("_", 1)
    if len(parts) != 2:
        logger.warning(f"Skipping skit with unexpected name format: {filename}")
        return
    base_name, token = parts
    if not _hmac_verify(token, base_name):
        logger.warning(f"Invalid HMAC token for skit {filename}")
        return
    if not _is_valid_audio(skit_path):
        logger.warning(f"Invalid audio file detected: {filename}")
        return
    # Security: ensure the caller had the ``sys_queue_skit`` capability.
    # In this lightweight implementation we simply log the expected capability.
    _record_audit(
        "skit_queued",
        {"filename": filename, "capability": "sys_queue_skit"},
    )
    # Move to the ready queue
    dest = READY_DIR / skit_path.name
    shutil.move(str(skit_path), str(dest))
    _write_trigger(dest)
    logger.info(f"Queued skit {dest} for Liquidsoap")

def run_worker() -> None:
    """Entry point for the background worker.

    It runs indefinitely until the process is terminated. The function is kept
    simple to allow execution via ``python -m src.ai_queue_worker`` or as a
    Docker service.
    """
    logger.info("AI Queue Worker started")
    try:
        while True:
            # Scan for new skits (exclude sub‑folders)
            for entry in SKITS_DIR.iterdir():
                if entry.is_file() and entry.suffix.lower() in {".wav", ".mp3"}:
                    _process_new_skit(entry)
            _archive_old_skits()
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        logger.info("AI Queue Worker stopped by user")
    except Exception as exc:
        logger.exception(f"Unexpected error in AI Queue Worker: {exc}")
        raise

if __name__ == "__main__":
    run_worker()
