"""Windows desktop / process adapter (Stage 1)."""

from __future__ import annotations

import subprocess
import sys
from typing import Any

from arbora.core.types import StepResult, new_id


class DesktopAdapter:
    name = "desktop"

    def execute(self, action: str, args: dict[str, Any], *, dry_run: bool = False) -> StepResult:
        if action == "list_running_apps":
            return self._list_running_apps(dry_run=dry_run)
        if action == "launch_app":
            return self._launch_app(str(args.get("name", "")), dry_run=dry_run)
        return StepResult(
            step_id=new_id("res_"),
            ok=False,
            output="",
            error=f"Unknown desktop action '{action}'",
            dry_run=dry_run,
        )

    def _list_running_apps(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output="[dry-run] Would list running applications",
                dry_run=True,
            )
        if sys.platform != "win32":
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="Desktop adapter currently targets Windows",
            )
        command = (
            "Get-Process | Where-Object { $_.MainWindowTitle } | "
            "Select-Object -First 25 ProcessName, Id, MainWindowTitle | "
            "Format-Table -AutoSize | Out-String"
        )
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if completed.returncode != 0:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=completed.stdout.strip(),
                error=completed.stderr.strip() or f"exit code {completed.returncode}",
            )
        return StepResult(step_id=new_id("res_"), ok=True, output=completed.stdout.strip())

    def _launch_app(self, name: str, *, dry_run: bool) -> StepResult:
        if not name:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="launch_app requires args.name",
                dry_run=dry_run,
            )
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would launch '{name}'",
                dry_run=True,
            )
        if sys.platform != "win32":
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="Desktop adapter currently targets Windows",
            )
        # Use Start-Process so we don't block on GUI apps.
        safe_name = name.replace("'", "''")
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Start-Process -FilePath '{safe_name}'"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if completed.returncode != 0:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=completed.stdout.strip(),
                error=completed.stderr.strip() or f"Failed to launch '{name}'",
            )
        return StepResult(
            step_id=new_id("res_"),
            ok=True,
            output=f"Launched '{name}'",
        )
