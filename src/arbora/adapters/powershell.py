"""Shared PowerShell execution helpers for Windows adapters."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass


DEFAULT_MAX_OUTPUT_CHARS = 12_000


@dataclass
class ShellOutcome:
    ok: bool
    stdout: str
    stderr: str
    returncode: int | None = None
    timed_out: bool = False
    error: str | None = None


def require_windows() -> str | None:
    if sys.platform != "win32":
        return "This adapter currently targets Windows"
    return None


def run_powershell(
    command: str,
    *,
    timeout_seconds: float = 30,
    max_output_chars: int = DEFAULT_MAX_OUTPUT_CHARS,
) -> ShellOutcome:
    """Run a PowerShell command and return a normalized outcome."""
    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        partial_out = ""
        if exc.stdout:
            partial_out = exc.stdout if isinstance(exc.stdout, str) else exc.stdout.decode("utf-8", "replace")
        partial_err = ""
        if exc.stderr:
            partial_err = exc.stderr if isinstance(exc.stderr, str) else exc.stderr.decode("utf-8", "replace")
        return ShellOutcome(
            ok=False,
            stdout=_truncate(partial_out.strip(), max_output_chars),
            stderr=_truncate(partial_err.strip(), max_output_chars),
            timed_out=True,
            error=f"PowerShell timed out after {timeout_seconds:g}s",
        )
    except FileNotFoundError:
        return ShellOutcome(
            ok=False,
            stdout="",
            stderr="",
            error="PowerShell executable not found on PATH",
        )
    except OSError as exc:
        return ShellOutcome(ok=False, stdout="", stderr="", error=f"Failed to start PowerShell: {exc}")

    stdout = _truncate((completed.stdout or "").strip(), max_output_chars)
    stderr = _truncate((completed.stderr or "").strip(), max_output_chars)
    ok = completed.returncode == 0
    error = None
    if not ok:
        error = stderr or f"PowerShell exited with code {completed.returncode}"
    return ShellOutcome(
        ok=ok,
        stdout=stdout,
        stderr=stderr,
        returncode=completed.returncode,
        error=error,
    )


def ps_quote(value: str) -> str:
    """Single-quote a string for safe inclusion in a PowerShell command."""
    return "'" + value.replace("'", "''") + "'"


def _truncate(text: str, limit: int) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    omitted = len(text) - limit
    return text[:limit] + f"\n...[truncated {omitted} chars]"
