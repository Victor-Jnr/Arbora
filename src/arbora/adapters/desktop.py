"""Windows desktop / process adapter."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from arbora.adapters.powershell import ps_quote, require_windows, run_powershell
from arbora.core.types import StepResult, new_id

# Common friendly names → launch targets (Start-Process / Appx aliases).
APP_ALIASES: dict[str, str] = {
    "notepad": "notepad.exe",
    "calc": "calc.exe",
    "calculator": "calc.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "explorer": "explorer.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "wordpad": "wordpad.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "msedge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "firefox": "firefox.exe",
    "code": "Code.exe",
    "vscode": "Code.exe",
    "visual studio code": "Code.exe",
    "discord": "Discord.exe",
    "spotify": "Spotify.exe",
    "wt": "wt.exe",
    "windows terminal": "wt.exe",
    "slack": "slack.exe",
}

_KNOWN_LAUNCH_PATHS: dict[str, tuple[str, ...]] = {
    "chrome": (
        r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
        r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
        r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
    ),
    "edge": (
        r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
    ),
    "firefox": (
        r"%ProgramFiles%\Mozilla Firefox\firefox.exe",
        r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe",
    ),
    "vscode": (
        r"%LocalAppData%\Programs\Microsoft VS Code\Code.exe",
        r"%ProgramFiles%\Microsoft VS Code\Code.exe",
    ),
    "discord": (r"%LocalAppData%\Discord\Discord.exe",),
    "spotify": (
        r"%AppData%\Spotify\Spotify.exe",
        r"%LocalAppData%\Microsoft\WindowsApps\Spotify.exe",
    ),
    "wt": (r"%LocalAppData%\Microsoft\WindowsApps\wt.exe",),
    "slack": (r"%LocalAppData%\slack\slack.exe",),
}

_EXE_TO_PATH_KEY = {
    "chrome.exe": "chrome",
    "msedge.exe": "edge",
    "firefox.exe": "firefox",
    "code.exe": "vscode",
    "discord.exe": "discord",
    "spotify.exe": "spotify",
    "wt.exe": "wt",
    "slack.exe": "slack",
}


def resolve_launch_target(name: str) -> str:
    """Map a friendly name to an exe or a known install path if it exists."""
    raw = name.strip()
    if not raw:
        return raw
    lowered = raw.lower()
    exe = APP_ALIASES.get(lowered, raw)
    key = _EXE_TO_PATH_KEY.get(exe.lower(), lowered if lowered in _KNOWN_LAUNCH_PATHS else "")
    for candidate in _KNOWN_LAUNCH_PATHS.get(key, ()):
        path = Path(os.path.expandvars(candidate))
        if path.is_file():
            return str(path)
    return exe


class DesktopAdapter:
    name = "desktop"

    def execute(self, action: str, args: dict[str, Any], *, dry_run: bool = False) -> StepResult:
        if action == "list_running_apps":
            return self._list_running_apps(dry_run=dry_run)
        if action == "launch_app":
            return self._launch_app(str(args.get("name", "")), dry_run=dry_run)
        if action == "focus_window":
            return self._focus_window(
                str(args.get("title_contains", args.get("name", ""))),
                dry_run=dry_run,
            )
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
                output="[dry-run] Would list running applications with visible windows",
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)

        command = (
            "Get-Process | Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle } | "
            "Sort-Object ProcessName | "
            "Select-Object -First 40 ProcessName, Id, MainWindowTitle | "
            "Format-Table -AutoSize | Out-String -Width 200"
        )
        outcome = run_powershell(command, timeout_seconds=30)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error,
            )
        output = outcome.stdout or "(no visible windows found)"
        return StepResult(step_id=new_id("res_"), ok=True, output=output)

    def _launch_app(self, name: str, *, dry_run: bool) -> StepResult:
        if not name.strip():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="launch_app requires args.name",
                dry_run=dry_run,
            )
        target = resolve_launch_target(name)
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would launch '{target}'",
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)

        quoted = ps_quote(target)
        # Resolve via Get-Command when possible, then Start-Process.
        command = (
            f"$target = {quoted}; "
            "$cmd = Get-Command -Name $target -ErrorAction SilentlyContinue; "
            "if ($cmd) { $target = $cmd.Source }; "
            "try { "
            "  Start-Process -FilePath $target -ErrorAction Stop | Out-Null; "
            "  Write-Output \"Launched: $target\" "
            "} catch { "
            "  Write-Error $_.Exception.Message; exit 1 "
            "}"
        )
        outcome = run_powershell(command, timeout_seconds=30)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or f"Failed to launch '{target}'",
            )
        return StepResult(
            step_id=new_id("res_"),
            ok=True,
            output=outcome.stdout or f"Launched '{target}'",
        )

    def _focus_window(self, title_contains: str, *, dry_run: bool) -> StepResult:
        needle = title_contains.strip()
        if not needle:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="focus_window requires args.title_contains or args.name",
                dry_run=dry_run,
            )
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would focus window containing '{needle}'",
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)

        quoted = ps_quote(needle)
        command = (
            "Add-Type -TypeDefinition @'\n"
            "using System;\n"
            "using System.Runtime.InteropServices;\n"
            "public class ArboraWin {\n"
            "  [DllImport(\"user32.dll\")] public static extern bool SetForegroundWindow(IntPtr hWnd);\n"
            "  [DllImport(\"user32.dll\")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);\n"
            "}\n"
            "'@ -ErrorAction SilentlyContinue; "
            f"$needle = {quoted}; "
            "$proc = Get-Process | Where-Object { "
            "  $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -and "
            "  ($_.MainWindowTitle -like ('*' + $needle + '*') -or $_.ProcessName -like ('*' + $needle + '*')) "
            "} | Select-Object -First 1; "
            "if (-not $proc) { Write-Error \"No window matched '$needle'\"; exit 1 }; "
            "[void][ArboraWin]::ShowWindowAsync($proc.MainWindowHandle, 9); "
            "[void][ArboraWin]::SetForegroundWindow($proc.MainWindowHandle); "
            "Write-Output (\"Focused: {0} (pid {1}) title={2}\" -f $proc.ProcessName, $proc.Id, $proc.MainWindowTitle)"
        )
        outcome = run_powershell(command, timeout_seconds=30)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or f"Failed to focus '{needle}'",
            )
        return StepResult(step_id=new_id("res_"), ok=True, output=outcome.stdout or f"Focused '{needle}'")
