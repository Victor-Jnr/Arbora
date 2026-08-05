"""PowerShell / terminal adapter — always invoked via the permission broker."""

from __future__ import annotations

from typing import Any

from arbora.adapters.powershell import require_windows, run_powershell
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
        if timeout_seconds < 1:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="timeout_seconds must be >= 1",
                dry_run=dry_run,
            )
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would run PowerShell: {command}",
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[non-windows stub] Skipped PowerShell: {command}",
            )

        outcome = run_powershell(command, timeout_seconds=timeout_seconds)
        return StepResult(
            step_id=new_id("res_"),
            ok=outcome.ok,
            output=outcome.stdout,
            error=outcome.error,
        )
