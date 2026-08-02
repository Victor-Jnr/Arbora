"""Ollama local model provider."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


DEFAULT_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "gpt-oss:20b"


class OllamaProvider:
    """Talks to a local Ollama daemon over HTTP. No cloud calls."""

    name = "ollama"

    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
        timeout_seconds: float = 180.0,
    ) -> None:
        self.model = model or os.environ.get("ARBORA_OLLAMA_MODEL", DEFAULT_MODEL)
        self.host = (host or os.environ.get("ARBORA_OLLAMA_HOST", DEFAULT_HOST)).rstrip("/")
        self.timeout_seconds = timeout_seconds

    def available(self) -> bool:
        try:
            payload = self._request("GET", "/api/tags")
            models = payload.get("models") or []
            names = {str(item.get("name", "")) for item in models}
            return any(
                name == self.model or name.startswith(f"{self.model}:") for name in names
            )
        except Exception:
            return False

    def complete(self, prompt: str) -> str:
        payload = self._request(
            "POST",
            "/api/chat",
            {
                "model": self.model,
                "stream": False,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are Arbora's local planner assistant. "
                            "Be concise. Prefer JSON when asked for JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            },
        )
        message = payload.get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        # Some models return a list of content parts.
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    parts.append(str(part.get("text", "")))
                elif isinstance(part, str):
                    parts.append(part)
            joined = "".join(parts).strip()
            if joined:
                return joined
        raise RuntimeError(f"Ollama returned no content for model '{self.model}'")

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self.host}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if body is not None else {},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Cannot reach Ollama at {self.host}. Is `ollama serve` running?"
            ) from exc
        return json.loads(raw) if raw else {}
