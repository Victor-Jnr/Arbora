"""Windows desktop / process adapter."""

from __future__ import annotations

import os
import re
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


CLIPBOARD_PREVIEW_CHARS = 120

_SECRET_MARKERS = (
    "password=",
    "passwd=",
    "pwd=",
    "secret=",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "bearer ",
    "authorization:",
    "private_key",
    "-----begin",
    "ghp_",
    "github_pat_",
    "glpat-",
    "xoxb-",
    "xoxp-",
    "sk-ant-",
    "sk-proj-",
    "akia",
)


def clipboard_looks_secret(text: str) -> bool:
    """True when clipboard text looks like a password, token, or key."""
    if not text or not text.strip():
        return False
    lower = text.lower()
    if any(marker in lower for marker in _SECRET_MARKERS):
        return True
    if re.search(r"(?i)(^|[\s\"'=])sk-[A-Za-z0-9]{10,}", text):
        return True
    stripped = text.strip()
    if stripped.count(".") == 2 and len(stripped) >= 40 and stripped.startswith("eyJ"):
        return True
    compact = "".join(stripped.split())
    if len(compact) >= 32 and all(char in "0123456789abcdefABCDEF" for char in compact):
        return True
    return False


def parse_clipboard_snapshot(stdout: str) -> dict[str, Any]:
    """Parse the structured Get-Clipboard snapshot written by PowerShell."""
    kind = "empty"
    length = 0
    width: int | None = None
    height: int | None = None
    files: list[str] = []
    capturing_text = False
    text_lines: list[str] = []
    for line in (stdout or "").splitlines():
        if capturing_text:
            text_lines.append(line)
            continue
        if line == "TEXT_BEGIN":
            capturing_text = True
            continue
        if line.startswith("KIND="):
            kind = line.split("=", 1)[1].strip().lower() or "empty"
        elif line.startswith("LENGTH="):
            try:
                length = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                length = 0
        elif line.startswith("WIDTH="):
            try:
                width = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                width = None
        elif line.startswith("HEIGHT="):
            try:
                height = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                height = None
        elif line.startswith("FILE="):
            files.append(line.split("=", 1)[1])
    text = "\n".join(text_lines)
    if kind == "text" and not length:
        length = len(text)
    if kind == "files" and not length:
        length = len(files)
    return {
        "kind": kind,
        "length": length,
        "width": width,
        "height": height,
        "files": files,
        "text": text,
    }


def format_clipboard_report(snapshot: dict[str, Any], *, reveal: bool) -> str:
    kind = str(snapshot.get("kind") or "empty")
    if kind == "empty":
        return "Clipboard is empty."
    if kind == "image":
        width = snapshot.get("width")
        height = snapshot.get("height")
        size = f" {width}x{height}" if width and height else ""
        return f"Clipboard holds an image{size}. Pixel data is not shown."
    if kind == "files":
        files = [str(item) for item in snapshot.get("files") or []]
        count = int(snapshot.get("length") or len(files))
        lines = [f"Clipboard holds {count} file path(s)."]
        lines.extend(f"  {name}" for name in files[:20])
        return "\n".join(lines)
    length = int(snapshot.get("length") or 0)
    text = str(snapshot.get("text") or "")
    if clipboard_looks_secret(text):
        return (
            f"Clipboard holds text ({length} chars). "
            "Content withheld because it looks like a secret (password, token, or key)."
        )
    if not reveal:
        return (
            f"Clipboard holds text ({length} chars). "
            "Content withheld; ask to show clipboard text for a short preview."
        )
    preview = text.replace("\r\n", "\n")
    if len(preview) > CLIPBOARD_PREVIEW_CHARS:
        preview = preview[:CLIPBOARD_PREVIEW_CHARS] + "…"
    return f"Clipboard text ({length} chars):\n{preview}"


def _clipboard_arg_reveal(args: dict[str, Any]) -> bool:
    value = args.get("reveal", False)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y"}


_CLIPBOARD_PS = (
    "$ErrorActionPreference = 'SilentlyContinue'; "
    "try { $drop = Get-Clipboard -Format FileDropList } catch { $drop = $null }; "
    "if ($drop) { "
    "  $names = @($drop | ForEach-Object { $_.ToString() }); "
    "  Write-Output 'KIND=files'; "
    "  Write-Output ('LENGTH=' + $names.Count); "
    "  $names | Select-Object -First 20 | ForEach-Object { Write-Output ('FILE=' + $_) }; "
    "} else { "
    "  try { $img = Get-Clipboard -Format Image } catch { $img = $null }; "
    "  if ($img) { "
    "    Write-Output 'KIND=image'; "
    "    Write-Output ('WIDTH=' + $img.Width); "
    "    Write-Output ('HEIGHT=' + $img.Height); "
    "  } else { "
    "    try { $text = Get-Clipboard -Raw } catch { $text = $null }; "
    "    if ($null -ne $text -and [string]$text -ne '') { "
    "      Write-Output 'KIND=text'; "
    "      Write-Output ('LENGTH=' + ([string]$text).Length); "
    "      Write-Output 'TEXT_BEGIN'; "
    "      Write-Output ([string]$text); "
    "    } else { "
    "      Write-Output 'KIND=empty'; "
    "      Write-Output 'LENGTH=0'; "
    "    } "
    "  } "
    "}"
)


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
        if action == "inspect_clipboard":
            return self._inspect_clipboard(reveal=_clipboard_arg_reveal(args), dry_run=dry_run)
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

    def _inspect_clipboard(self, *, reveal: bool, dry_run: bool) -> StepResult:
        if dry_run:
            if reveal:
                output = (
                    "[dry-run] Would inspect the clipboard and show a short text preview "
                    "unless it looks like a secret"
                )
            else:
                output = "[dry-run] Would inspect the clipboard (type and length only; content withheld)"
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=output,
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        outcome = run_powershell(_CLIPBOARD_PS, timeout_seconds=15)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or "Failed to read the clipboard",
            )
        snapshot = parse_clipboard_snapshot(outcome.stdout)
        return StepResult(
            step_id=new_id("res_"),
            ok=True,
            output=format_clipboard_report(snapshot, reveal=reveal),
        )
