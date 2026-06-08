import os
from typing import List, Optional, Tuple

import httpx

KNOWN_ENDPOINTS = [
	"http://host.docker.internal:11434",
	"http://localhost:11434",
	"http://ollama:11434",
]

PREFERRED_MODELS = ["qwen2.5-coder:7b", "llama3.1:8b"]


class OllamaClient:
	def __init__(self):
		self.base: Optional[str] = None
		self.model: Optional[str] = None

	async def autodetect(self) -> Tuple[Optional[str], Optional[str]]:
		async with httpx.AsyncClient(timeout=5.0) as client:
			for base in KNOWN_ENDPOINTS:
				try:
					r = await client.get(f"{base}/api/tags")
					if r.status_code == 200:
						tags = r.json()
						# pick best model
						for m in PREFERRED_MODELS:
							if m in tags:
								self.base = base
								self.model = m
								return self.base, self.model
						# fallback to any installed model
						if isinstance(tags, list) and tags:
							self.base = base
							self.model = tags[0]
							return self.base, self.model
				except Exception:
					continue
		return None, None

	async def status(self) -> dict:
		return {"base": self.base, "model": self.model}

	async def generate(self, prompt: str, model: Optional[str] = None) -> str:
		if not self.base:
			await self.autodetect()
		if not self.base:
			raise RuntimeError("No Ollama endpoint detected")
		model_to_use = model or self.model
		if not model_to_use:
			raise RuntimeError("No Ollama model available")
		async with httpx.AsyncClient(timeout=60.0) as client:
			try:
				payload = {"model": model_to_use, "prompt": prompt}
				r = await client.post(f"{self.base}/api/generate", json=payload)
				r.raise_for_status()
				# Ollama streams; for simplicity return text body or json
				try:
					return r.json()
				except Exception:
					return r.text
			except Exception as e:
				raise


CLIENT = OllamaClient()


async def generate(prompt: str, model: Optional[str] = None) -> str:
	return await CLIENT.generate(prompt, model)


async def autodetect() -> Tuple[Optional[str], Optional[str]]:
	return await CLIENT.autodetect()


async def status() -> dict:
	return await CLIENT.status()
