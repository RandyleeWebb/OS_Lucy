import os
import uuid
import asyncio
import subprocess
import logging
from typing import Dict, Any, Optional

from bus import publish
from audit import append_audit

logger = logging.getLogger("emma.terminal.sessions")


class TerminalSession:
	def __init__(self, shell: str = "/bin/bash"):
		self.id = uuid.uuid4().hex
		self.shell = shell
		self.master_fd: Optional[int] = None
		self.process: Optional[subprocess.Popen] = None
		self.queue: asyncio.Queue = asyncio.Queue()
		self._closed = False

	def start(self) -> None:
		# Open a new pty
		master_fd, slave_fd = os.openpty()
		# Launch the shell attached to the slave side
		proc = subprocess.Popen(
			[self.shell],
			stdin=slave_fd,
			stdout=slave_fd,
			stderr=slave_fd,
			close_fds=True,
			preexec_fn=os.setsid,
		)
		# Parent keeps master fd
		os.close(slave_fd)
		# Set non-blocking
		try:
			os.set_blocking(master_fd, False)
		except Exception:
			pass

		self.master_fd = master_fd
		self.process = proc

		loop = asyncio.get_running_loop()
		# Register reader callback to stream output into queue and publish events
		loop.add_reader(master_fd, self._on_output)

	def _on_output(self) -> None:
		# Called in event loop when master_fd is readable
		try:
			data = os.read(self.master_fd, 4096)
		except OSError as e:
			logger.warning("Error reading from pty for session %s: %s", self.id, e)
			data = b""

		if not data:
			# EOF — process may have exited
			asyncio.get_running_loop().call_soon_threadsafe(asyncio.create_task, self._handle_exit())
			return

		text = data.decode("utf-8", errors="replace")
		# Put into queue for websocket consumers
		try:
			asyncio.get_running_loop().call_soon_threadsafe(self.queue.put_nowait, text)
		except Exception:
			# In case queue isn't ready, ignore
			pass

		# Publish terminal output event (best-effort)
		try:
			asyncio.get_running_loop().call_soon_threadsafe(asyncio.create_task, publish("terminal:output", {"session": self.id, "output": text}))
			# also append to audit log
			append_audit("terminal.output", {"session": self.id, "output": text}, source="emma")
		except Exception:
			logger.exception("Failed to publish terminal output for session %s", self.id)

	async def _handle_exit(self) -> None:
		# Clean up when process exits
		await self.queue.put("\n[session closed]\n")
		self.close()

	def write(self, data: str) -> None:
		if self.master_fd is None:
			raise RuntimeError("Session not started")
		try:
			os.write(self.master_fd, data.encode())
		except Exception as e:
			logger.warning("Error writing to pty for session %s: %s", self.id, e)

	def close(self) -> None:
		if self._closed:
			return
		self._closed = True
		try:
			if self.master_fd is not None:
				try:
					loop = asyncio.get_running_loop()
					loop.remove_reader(self.master_fd)
				except Exception:
					pass
				try:
					os.close(self.master_fd)
				except Exception:
					pass
				self.master_fd = None
		finally:
			try:
				if self.process and self.process.poll() is None:
					self.process.terminate()
			except Exception:
				pass


class SessionManager:
	def __init__(self):
		self._sessions: Dict[str, TerminalSession] = {}

	def create(self, shell: str = "/bin/bash") -> TerminalSession:
		sess = TerminalSession(shell=shell)
		sess.start()
		self._sessions[sess.id] = sess
		logger.info("Created terminal session %s", sess.id)
		return sess

	def get(self, session_id: str) -> Optional[TerminalSession]:
		return self._sessions.get(session_id)

	def list(self) -> Dict[str, Any]:
		return {sid: {"shell": s.shell, "pid": (s.process.pid if s.process else None)} for sid, s in self._sessions.items()}

	def close(self, session_id: str) -> bool:
		s = self._sessions.pop(session_id, None)
		if not s:
			return False
		s.close()
		logger.info("Closed terminal session %s", session_id)
		return True


manager = SessionManager()
