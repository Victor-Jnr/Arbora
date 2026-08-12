"""Opt-in OpenAI-compatible cloud provider."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"


class OpenAICompatibleProvider:
    """OpenAI-compatible chat completions API (opt-in; data leaves the machine)."""

    name = "openai"
    data_leaves_machine = True

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 120.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("ARBORA_OPENAI_API_KEY", "").strip()
        self.base_url = (base_url or os.environ.get("ARBORA_OPENAI_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
        self.model = model or os.environ.get("ARBORA_OPENAI_MODEL", DEFAULT_MODEL)
        self.timeout_seconds = timeout_seconds

    def available(self) -> bool:
        return bool(self.api_key)

    def privacy_notice(self) -> str:
        return (
            "Cloud provider active — your prompt and plan context are sent to "
            f"{self.base_url} as model '{self.model}'."
        )

    def complete(self, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError(
                "OpenAI-compatible provider requires ARBORA_OPENAI_API_KEY to be set."
            )
        payload = self._request(
            "POST",
            "/chat/completions",
            {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are Arbora's planner assistant. Be concise. "
                            "Prefer JSON when asked for JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            },
        )
        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError("Cloud provider returned no choices")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        raise RuntimeError("Cloud provider returned empty content")

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Cloud API HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Cannot reach cloud API at {self.base_url}") from exc
        return json.loads(raw) if raw else {}


def cloud_provider_configured() -> bool:
    return bool(os.environ.get("ARBORA_OPENAI_API_KEY", "").strip())
