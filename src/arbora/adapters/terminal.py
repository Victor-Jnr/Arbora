"""PowerShell / terminal adapter — always invoked via the permission broker."""

from __future__ import annotations

import subprocess
import sys
from typing import Any

from arbora.core.types import StepResult, new_id


class TerminalAdapter:
    name = "terminal"

    def execute(self, action: str, args: dict[str, Any], *, dry_run: bool = False) -> StepResult:
        if action == "run_powershell":
            return self._run_powershell(
                str(args.get("command", "")),
                timeout_seconds=int(args.get("timeout_seconds", 60)),
                dry_run=dry_run,
            )
        return StepResult(
            step_id=new_id("res_"),
            ok=False,
            output="",
            error=f"Unknown terminal action '{action}'",
            dry_run=dry_run,
        )

    def _run_powershell(self, command: str, *, timeout_seconds: int, dry_run: bool) -> StepResult:
        if not command.strip():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="run_powershell requires args.command",
                dry_run=dry_run,
            )
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would run PowerShell: {command}",
                dry_run=True,
            )
        if sys.platform != "win32":
            # Allow non-Windows CI/dev by falling back to a no-op shell echo.
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[non-windows stub] Skipped PowerShell: {command}",
            )
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        ok = completed.returncode == 0
        return StepResult(
            step_id=new_id("res_"),
            ok=ok,
            output=(completed.stdout or "").strip(),
            error=(completed.stderr or "").strip() or (None if ok else f"exit code {completed.returncode}"),
        )
