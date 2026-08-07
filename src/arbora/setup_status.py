"""Probe readiness of optional local services used by Arbora."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Light(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


LIGHT_HEX = {
    Light.GREEN: "#52B788",
    Light.YELLOW: "#E9C46A",
    Light.RED: "#E76F51",
}


@dataclass(frozen=True)
class ServiceStatus:
    name: str
    light: Light
    detail: str


def probe_ollama() -> ServiceStatus:
    try:
        from arbora.providers.ollama import OllamaProvider

        provider = OllamaProvider()
        # Reachability vs model presence.
        try:
            payload = provider._request("GET", "/api/tags")
        except Exception:
            return ServiceStatus("Ollama", Light.RED, "daemon unreachable")
        models = payload.get("models") or []
        names = {str(item.get("name", "")) for item in models}
        if any(name == provider.model or name.startswith(f"{provider.model}:") for name in names):
            return ServiceStatus("Ollama", Light.GREEN, f"model {provider.model}")
        if models:
            return ServiceStatus(
                "Ollama",
                Light.YELLOW,
                f"up, missing {provider.model}",
            )
        return ServiceStatus("Ollama", Light.YELLOW, "up, no models")
    except Exception as exc:
        return ServiceStatus("Ollama", Light.RED, str(exc)[:80])


def probe_playwright() -> ServiceStatus:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return ServiceStatus("Playwright", Light.RED, "package not installed")

    try:
        pw = sync_playwright().start()
        try:
            exe = Path(pw.chromium.executable_path)
            if exe.exists():
                return ServiceStatus("Playwright", Light.GREEN, "Chromium ready")
            return ServiceStatus("Playwright", Light.YELLOW, "Chromium not installed")
        finally:
            pw.stop()
    except Exception as exc:
        message = str(exc).lower()
        if "executable doesn't exist" in message or "browser" in message:
            return ServiceStatus("Playwright", Light.YELLOW, "Chromium not installed")
        return ServiceStatus("Playwright", Light.RED, str(exc)[:80])


def probe_memory() -> ServiceStatus:
    try:
        import tempfile

        from arbora.memory import LocalMemoryStore

        with tempfile.TemporaryDirectory() as tmp:
            store = LocalMemoryStore(root=Path(tmp), force_file_key=True)
            backend = store.key_backend
        return ServiceStatus("Memory", Light.GREEN, f"encrypted ({backend})")
    except Exception as exc:
        return ServiceStatus("Memory", Light.RED, str(exc)[:80])


def probe_all() -> list[ServiceStatus]:
    return [probe_memory(), probe_ollama(), probe_playwright()]


def install_playwright_chromium() -> tuple[bool, str]:
    """Install Chromium for Playwright into the current environment."""
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False, "Playwright package missing. Run: pip install playwright"

    completed = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
    if completed.returncode != 0:
        return False, output or f"exit code {completed.returncode}"
    return True, output or "Chromium installed"
