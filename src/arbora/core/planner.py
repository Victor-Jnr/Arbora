"""Goal planner — turns natural-language goals into inspectable tool plans.

Known journeys use deterministic templates. Unmatched goals may use a model
provider (e.g. local Ollama) to propose a JSON plan, which is validated before
returning. Models propose; the permission broker still disposes.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from arbora.core.tool_catalog import ALLOWED_ACTIONS
from arbora.core.types import Plan, Sensitivity, ToolStep, new_id
from arbora.providers.base import ModelProvider
from arbora.voice.windows import sanitize_speech_text
from arbora.workflows.packs import match_workflow_pack

SENSITIVITY_VALUES = {item.value: item for item in Sensitivity}

DRIVE_SIZE_WALK_TIMEOUT_SECONDS = 300


def _user_temp_dir() -> Path:
    raw = os.environ.get("TEMP") or os.environ.get("TMP") or tempfile.gettempdir()
    return Path(raw).expanduser().resolve(strict=False)


def powershell_is_destructive(command: str) -> bool:
    """True for deletes, format-volume, and shutdown — not Format-Table."""
    text = command.lower()
    markers = (
        "remove-item",
        "rmdir",
        "clear-disk",
        "format-volume",
        "stop-computer",
        "restart-computer",
        "reset-computer",
        "clear-content",
    )
    if any(token in text for token in markers):
        return True
    if re.search(r"(^|[\s;&(|])del\s+", text):
        return True
    if re.search(r"(^|[\s;&(|])rm\s+", text):
        return True
    if re.search(r"(^|[\s;&(|])format\s+[a-z]:", text):
        return True
    return False


def looks_like_drive_size_walk(command: str) -> bool:
    text = command.lower()
    has_walk = any(token in text for token in ("get-childitem", "getfolder", "robocopy"))
    has_size = any(token in text for token in ("length", ".size", "measure-object", "/bytes", "1gb", "1mb"))
    has_root = re.search(r"[a-z]:\\", text) is not None
    return bool(has_walk and has_size and has_root)


class GoalPlanner:
    def __init__(
        self,
        provider: ModelProvider | None = None,
        *,
        workday_root: Path | None = None,
        briefs_root: Path | None = None,
        projects_root: Path | None = None,
        downloads_root: Path | None = None,
        notes_root: Path | None = None,
        spoken_confirmations: bool = False,
    ) -> None:
        self._provider = provider
        self._workday_root = workday_root
        self._briefs_root = briefs_root
        self._projects_root = projects_root
        self._downloads_root = downloads_root
        self._notes_root = notes_root
        self._spoken_confirmations = spoken_confirmations

    def _downloads_dir(self) -> Path:
        return self._downloads_root or Path.home() / "Downloads"

    def _documents_dir(self) -> Path:
        return Path.home() / "Documents"

    def _notes_dir(self) -> Path:
        return self._notes_root or Path.home() / "ArboraNotes"

    def plan(self, goal: str) -> Plan:
        return self._maybe_add_spoken_confirmation(self._draft_plan(goal))

    def _draft_plan(self, goal: str) -> Plan:
        text = goal.strip()
        lower = text.lower()

        if self._looks_like_spoken_confirmation(lower):
            return self._spoken_confirmation_plan(text)
        if self._looks_like_workday_start(lower):
            return self._workday_start_plan(text)
        if self._looks_like_workday_shutdown(lower):
            return self._workday_shutdown_plan(text)
        if self._looks_like_largest_folders(lower):
            return self._largest_folders_plan(text)
        if self._looks_like_network_status(lower):
            return self._network_status_plan(text)
        if self._looks_like_battery_status(lower):
            return self._battery_status_plan(text)
        if self._looks_like_printer_status(lower):
            return self._printer_status_plan(text)
        if self._looks_like_startup_apps(lower):
            return self._startup_apps_plan(text)
        if self._looks_like_default_browser(lower):
            return self._default_browser_plan(text)
        if self._looks_like_display_status(lower):
            return self._display_status_plan(text)
        if self._looks_like_windows_update(lower):
            return self._windows_update_plan(text)
        if self._looks_like_diagnostic(lower):
            return self._diagnostic_plan(text)
        if self._looks_like_dev_setup(lower):
            return self._dev_setup_plan(text)
        if self._looks_like_organise_downloads(lower):
            return self._organise_downloads_plan(text)
        if self._looks_like_undo_organise(lower):
            return self._undo_organise_plan(text)
        if self._looks_like_save_clipboard(lower):
            return self._save_clipboard_plan(text)
        if self._looks_like_copy_move(lower):
            return self._copy_move_plan(text)
        if self._looks_like_old_downloads(lower):
            return self._old_downloads_plan(text)
        if self._looks_like_save_note(lower):
            return self._save_note_plan(text)
        if self._looks_like_open_explorer(lower):
            return self._open_explorer_plan(text)
        if self._looks_like_recycle_bin(lower):
            return self._recycle_bin_plan(text)
        if self._looks_like_find_files(lower):
            return self._find_files_plan(text)
        if self._looks_like_temp(lower):
            return self._temp_plan(text)
        if self._looks_like_close_window(lower):
            return self._close_window_plan(text)
        if self._looks_like_open_in_browser(lower):
            return self._open_in_browser_plan(text)
        if self._looks_like_launch_app(lower):
            return self._launch_app_plan(text)
        if self._looks_like_clipboard(lower):
            return self._clipboard_plan(text)
        if self._looks_like_screenshot(lower):
            return self._screenshot_plan(text)
        if self._looks_like_recent_files(lower):
            return self._recent_files_plan(text)
        if self._looks_like_list_files(lower):
            return self._list_files_plan(text)
        if self._looks_like_research(lower, text):
            return self._research_plan(text)
        if self._looks_like_run_tests(lower):
            return self._run_tests_plan(text)
        if self._looks_like_terminal(lower):
            return self._terminal_plan(text)

        pack = match_workflow_pack(text)
        if pack is not None:
            plan = pack.to_plan(text)
            if plan is not None:
                return plan

        model_plan = self._plan_with_provider(text)
        if model_plan is not None:
            return model_plan

        return self._fallback_context_plan(text)

    def _plan_with_provider(self, goal: str) -> Plan | None:
        provider = self._provider
        if provider is None:
            return None
        # EchoProvider is a stub — skip unless it is a real backend.
        if getattr(provider, "name", "") == "echo-local":
            return None
        available = getattr(provider, "available", None)
        if callable(available) and not available():
            return None

        prompt = self._provider_prompt(goal)
        try:
            raw = provider.complete(prompt)
        except Exception:
            return None

        parsed = self._extract_json_object(raw)
        if parsed is None:
            return None
        return self._plan_from_provider_json(goal, parsed)

    def _provider_prompt(self, goal: str) -> str:
        catalog = {
            adapter: sorted(actions) for adapter, actions in ALLOWED_ACTIONS.items()
        }
        return (
            "Propose an Arbora tool plan for the user goal.\n"
            "Return ONLY a JSON object with keys: rationale (string), steps (array).\n"
            "Each step: adapter, action, args (object), summary, sensitivity, side_effects (array of strings).\n"
            f"Allowed adapters/actions: {json.dumps(catalog)}\n"
            "sensitivity must be one of: read, mutate, destructive, credential, financial.\n"
            "Prefer read-only diagnostics first. Never invent adapters or actions.\n"
            "Keep plans short (1-5 steps).\n"
            "Format-Table / Format-List are display cmdlets, not disk format. "
            "Get-ChildItem, Get-PSDrive, Measure-Object, and FileSystemObject folder sizes are sensitivity=read.\n"
            "Sizing every top-level folder on a drive needs timeout_seconds of at least 300; do not recurse the whole tree in one Get-ChildItem.\n"
            f"User goal: {goal}\n"
        )

    def _plan_from_provider_json(self, goal: str, data: dict[str, Any]) -> Plan | None:
        raw_steps = data.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            return None

        steps: list[ToolStep] = []
        for item in raw_steps[:8]:
            if not isinstance(item, dict):
                return None
            adapter = str(item.get("adapter", "")).strip()
            action = str(item.get("action", "")).strip()
            if adapter not in ALLOWED_ACTIONS or action not in ALLOWED_ACTIONS[adapter]:
                return None
            args = dict(item.get("args") if isinstance(item.get("args"), dict) else {})
            sens_raw = str(item.get("sensitivity", "read")).strip().lower()
            sensitivity = SENSITIVITY_VALUES.get(sens_raw, Sensitivity.READ)
            if adapter == "terminal" and action == "run_powershell":
                command = str(args.get("command", ""))
                if powershell_is_destructive(command):
                    sensitivity = Sensitivity.DESTRUCTIVE
                elif sensitivity == Sensitivity.DESTRUCTIVE:
                    sensitivity = Sensitivity.READ
                if looks_like_drive_size_walk(command):
                    try:
                        current = int(args.get("timeout_seconds", 60) or 60)
                    except (TypeError, ValueError):
                        current = 60
                    args["timeout_seconds"] = max(current, DRIVE_SIZE_WALK_TIMEOUT_SECONDS)
            side = item.get("side_effects") if isinstance(item.get("side_effects"), list) else []
            steps.append(
                ToolStep(
                    id=new_id("step_"),
                    adapter=adapter,
                    action=action,
                    args=args,
                    summary=str(item.get("summary") or f"{adapter}.{action}"),
                    sensitivity=sensitivity,
                    side_effects=tuple(str(s) for s in side),
                )
            )

        rationale = str(data.get("rationale") or "Plan proposed by local model provider.")
        provider_name = getattr(self._provider, "name", "provider")
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=f"[{provider_name}] {rationale}",
            steps=steps,
        )

    @staticmethod
    def _extract_json_object(text: str) -> dict[str, Any] | None:
        text = text.strip()
        if not text:
            return None
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None

    def _fallback_context_plan(self, text: str) -> Plan:
        downloads = self._downloads_dir()
        return Plan(
            id=new_id("plan_"),
            goal=text,
            rationale=(
                "No specialised journey matched and no usable model plan was produced. "
                "Offering a read-only context gathering plan."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="list_running_apps",
                    args={},
                    summary="List currently running applications",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Observes process list",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="list_directory",
                    args={"path": str(downloads)},
                    summary=f"List files in {downloads}",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads directory listing",),
                ),
            ],
        )

    def _workday_start_plan(self, goal: str) -> Plan:
        work_root = self._workday_root or Path.home() / "ArboraWorkday"
        briefing = work_root / "morning-briefing.txt"
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Workday setup journey (read → prepare → launch). "
                "1) Observe running apps. 2) Ensure work folder + morning note. "
                "3) Launch and focus a notes stand-in. No apps are closed."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="list_running_apps",
                    args={},
                    summary="Inspect which apps are already running",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Observes process list",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="ensure_directory",
                    args={"path": str(work_root)},
                    summary="Ensure ArboraWorkday folder exists",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("May create a directory under your home folder",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="write_text",
                    args={
                        "path": str(briefing),
                        "content": (
                            "Morning briefing\n"
                            "================\n"
                            "- Review calendar and unread mail (manual).\n"
                            "- Open priority docs from yesterday's resume note.\n"
                            "- Keep dry-run on until this routine is trusted.\n"
                        ),
                    },
                    summary=f"Write morning briefing stub to {briefing.name}",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Creates or overwrites a text file",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="launch_app",
                    args={"name": "notepad"},
                    summary="Launch Notepad as a stand-in for your notes app",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Starts a process",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="focus_window",
                    args={"title_contains": "Notepad"},
                    summary="Focus the Notepad window if it is open",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Brings an existing window to the foreground",),
                ),
            ],
        )

    def _workday_shutdown_plan(self, goal: str) -> Plan:
        work_root = self._workday_root or Path.home() / "ArboraWorkday"
        note_path = work_root / "resume-tomorrow.txt"
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Workday shutdown journey. "
                "1) Park a resume note. 2) List running apps for a manual close pass. "
                "Arbora does not force-quit apps in this journey."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="ensure_directory",
                    args={"path": str(work_root)},
                    summary="Ensure ArboraWorkday folder exists",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("May create a directory under your home folder",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="write_text",
                    args={
                        "path": str(note_path),
                        "content": (
                            "Resume tomorrow\n"
                            "==============\n"
                            "- Continue open tasks from today.\n"
                            "- Re-run 'start my workday' after approving the plan once.\n"
                        ),
                    },
                    summary=f"Write resume note to {note_path.name}",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Creates or overwrites a text file",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="list_running_apps",
                    args={},
                    summary="List running apps before any close requests",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Observes process list",),
                ),
            ],
        )

    def _largest_folders_plan(self, goal: str) -> Plan:
        root = self._drive_root_from_goal(goal)
        quoted = "'" + root.replace("'", "''") + "'"
        drive_name = root[0]
        command = (
            f"$root = {quoted}; "
            "$fso = New-Object -ComObject Scripting.FileSystemObject; "
            "$skip = @('System Volume Information','$Recycle.Bin','Recovery'); "
            "$rows = @(Get-ChildItem -LiteralPath $root -Directory -Force -ErrorAction SilentlyContinue | "
            "ForEach-Object { "
            "if ($skip -contains $_.Name) { "
            "[PSCustomObject]@{ Folder = $_.FullName; GB = $null } "
            "} else { "
            "try { "
            "[PSCustomObject]@{ Folder = $_.FullName; "
            "GB = [math]::Round(([int64]$fso.GetFolder($_.FullName).Size)/1GB, 2) } "
            "} catch { "
            "[PSCustomObject]@{ Folder = $_.FullName; GB = $null } "
            "} } }); "
            "$rows | Sort-Object GB -Descending | Format-Table -AutoSize | Out-String; "
            "$top = $rows | Where-Object { $null -ne $_.GB } | Sort-Object GB -Descending | "
            "Select-Object -First 1; "
            "if ($top) { \"Largest top-level folder: $($top.Folder) — $($top.GB) GB\" } "
            "else { 'Could not measure any folders (access denied or empty).' }"
        )
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Largest-folder journey — read-only. "
                f"Sizes each immediate subfolder of {root} (skips recycle bin / system volume). "
                "This can take a few minutes; it does not delete or move files."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="terminal",
                    action="run_powershell",
                    args={
                        "command": (
                            f"Get-PSDrive -Name {drive_name} | "
                            "Select-Object Name, "
                            "@{N='UsedGB';E={[math]::Round(($_.Used/1GB),2)}}, "
                            "@{N='FreeGB';E={[math]::Round(($_.Free/1GB),2)}} | "
                            "Format-Table | Out-String"
                        ),
                        "timeout_seconds": 30,
                    },
                    summary=f"Read-only: {drive_name}: used and free space (GB)",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Runs a read-only PowerShell query",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="terminal",
                    action="run_powershell",
                    args={
                        "command": command,
                        "timeout_seconds": DRIVE_SIZE_WALK_TIMEOUT_SECONDS,
                    },
                    summary=(
                        f"Read-only: size each top-level folder on {root} "
                        "(may take several minutes)"
                    ),
                    sensitivity=Sensitivity.READ,
                    side_effects=("Walks files under each top-level folder to sum sizes",),
                ),
            ],
        )

    def _network_status_plan(self, goal: str) -> Plan:
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Network inspect journey — read-only adapter, IPv4, and connection profile listing. "
                "Does not show Wi-Fi passwords, change adapters, or send packets beyond local queries."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="inspect_network",
                    args={},
                    summary="Read-only: list adapters, IPv4 addresses, and connection profiles",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads local network configuration; no Wi-Fi keys",),
                )
            ],
        )

    def _battery_status_plan(self, goal: str) -> Plan:
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Battery inspect journey — read-only charge and chassis/power status. "
                "Does not change power settings, run powercfg reports, or show serials."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="inspect_battery",
                    args={},
                    summary="Read-only: battery charge and AC/chassis status",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads Win32_Battery / computer-system chassis type",),
                )
            ],
        )

    def _printer_status_plan(self, goal: str) -> Plan:
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Printer inspect journey — read-only installed printers and the default. "
                "Does not send print jobs, change queues, or show driver/secret paths."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="inspect_printers",
                    args={},
                    summary="Read-only: list printers and the default printer",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads Win32_Printer names and status",),
                )
            ],
        )

    def _startup_apps_plan(self, goal: str) -> Plan:
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Startup inspect journey — read-only HKCU/HKLM Run names and the user Startup folder. "
                "Does not enable, disable, or delete entries, and does not list scheduled tasks."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="inspect_startup",
                    args={},
                    summary="Read-only: list startup apps (Run keys and Startup folder)",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads Run registry value names and Startup folder file names",),
                )
            ],
        )

    def _default_browser_plan(self, goal: str) -> Plan:
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Default-browser inspect journey — read-only http(s) UserChoice ProgId. "
                "Does not change the default browser or show the association Hash."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="inspect_default_browser",
                    args={},
                    summary="Read-only: default http(s) browser association",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads HKCU UserChoice ProgId for http and https",),
                )
            ],
        )

    def _display_status_plan(self, goal: str) -> Plan:
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Display inspect journey — read-only attached displays and resolutions. "
                "Does not change display mode, DPI, or wallpaper."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="inspect_display",
                    args={},
                    summary="Read-only: list displays and resolutions",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads Screen.AllScreens bounds; no mode changes",),
                )
            ],
        )

    def _windows_update_plan(self, goal: str) -> Plan:
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Windows Update inspect journey — read-only last hotfix install date. "
                "Does not install, download, or scan for updates, and does not dump every KB."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="inspect_windows_update",
                    args={},
                    summary="Read-only: last Windows Update install date",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads Get-HotFix InstalledOn for the latest dated item",),
                )
            ],
        )

    def _diagnostic_plan(self, goal: str) -> Plan:
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "PC troubleshooting journey — read-only diagnostics only. "
                "Reports disk, memory, and basic network reachability. "
                "No repairs, deletes, or registry changes; approve a separate plan for fixes."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="terminal",
                    action="run_powershell",
                    args={
                        "command": (
                            "Get-PSDrive -PSProvider FileSystem | "
                            "Select-Object Name, "
                            "@{N='UsedGB';E={[math]::Round(($_.Used/1GB),2)}}, "
                            "@{N='FreeGB';E={[math]::Round(($_.Free/1GB),2)}} | "
                            "Format-Table | Out-String"
                        ),
                        "timeout_seconds": 30,
                    },
                    summary="Read-only: free disk space per drive (GB)",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Runs a read-only PowerShell query",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="terminal",
                    action="run_powershell",
                    args={
                        "command": (
                            "Get-Process | Sort-Object WorkingSet64 -Descending | "
                            "Select-Object -First 10 Name, Id, "
                            "@{N='MB';E={[math]::Round($_.WorkingSet64/1MB,1)}} | "
                            "Format-Table | Out-String"
                        ),
                        "timeout_seconds": 30,
                    },
                    summary="Read-only: top processes by memory",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Runs a read-only PowerShell query",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="terminal",
                    action="run_powershell",
                    args={
                        "command": (
                            "try { "
                            "$r = Test-Connection -ComputerName 1.1.1.1 -Count 1 -Quiet -ErrorAction Stop; "
                            "if ($r) { 'Network: ping 1.1.1.1 OK' } else { 'Network: ping 1.1.1.1 failed' } "
                            "} catch { \"Network: probe error — $($_.Exception.Message)\" }"
                        ),
                        "timeout_seconds": 20,
                    },
                    summary="Read-only: basic network reachability probe",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Sends one ICMP echo request to 1.1.1.1",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="inspect_network",
                    args={},
                    summary="Read-only: network adapters, IPv4, and connection profiles",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads local adapter and IP configuration; no Wi-Fi keys",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="inspect_battery",
                    args={},
                    summary="Read-only: battery charge and AC/chassis status",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads Win32_Battery / computer-system chassis type",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="list_running_apps",
                    args={},
                    summary="List running applications for context",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Observes process list",),
                ),
            ],
        )

    def _dev_setup_plan(self, goal: str) -> Plan:
        project_root = Path.cwd()
        projects_root = self._projects_root or Path.home() / "ArboraProjects"
        readme_path = project_root / "README.md"
        gitignore_path = project_root / ".gitignore"
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Developer setup journey — inspect first, then scaffold starter files. "
                "1) Toolchain versions. 2) Current directory listing. "
                "3) Ensure ArboraProjects exists. 4) Write README.md and .gitignore stubs. "
                "Install/clone/venv commands are not auto-run; ask explicitly to run them."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="terminal",
                    action="run_powershell",
                    args={
                        "command": (
                            "@('python','git','node') | ForEach-Object { "
                            "$cmd = $_; "
                            "try { & $cmd --version 2>$null | ForEach-Object { \"$cmd $_\" } } "
                            "catch { \"$cmd not found\" } "
                            "}; Write-Output 'toolchain check complete'"
                        ),
                        "timeout_seconds": 30,
                    },
                    summary="Check local toolchain versions (python/git/node)",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Runs version queries in PowerShell",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="list_directory",
                    args={"path": str(project_root)},
                    summary=f"List files in {project_root}",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads directory listing",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="ensure_directory",
                    args={"path": str(projects_root)},
                    summary=f"Ensure projects folder exists at {projects_root}",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("May create a directory under your home folder",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="write_text",
                    args={
                        "path": str(readme_path),
                        "content": (
                            "# Project\n\n"
                            "Started with Arbora developer setup journey.\n\n"
                            "## Next steps\n\n"
                            "- Review generated files.\n"
                            "- Initialize git if needed.\n"
                            "- Add your application code.\n"
                        ),
                    },
                    summary=f"Write starter README.md to {readme_path.name}",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Creates or overwrites README.md",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="write_text",
                    args={
                        "path": str(gitignore_path),
                        "content": (
                            ".venv/\n"
                            "__pycache__/\n"
                            "*.pyc\n"
                            ".env\n"
                            ".pytest_cache/\n"
                            ".mypy_cache/\n"
                            ".DS_Store\n"
                            "Thumbs.db\n"
                        ),
                    },
                    summary=f"Write starter .gitignore to {gitignore_path.name}",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Creates or overwrites .gitignore",),
                ),
            ],
        )

    def _organise_downloads_plan(self, goal: str) -> Plan:
        downloads = self._downloads_dir()
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "File organisation journey — preview first, then apply moves. "
                "An undo batch is recorded so you can reverse with 'undo last organise'."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="list_directory",
                    args={"path": str(downloads)},
                    summary=f"Preview contents of {downloads}",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads directory listing",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="preview_organise",
                    args={"path": str(downloads)},
                    summary=f"Preview filing groups for {downloads} (dry classification)",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Classifies filenames in memory; no moves yet",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="apply_organise",
                    args={"path": str(downloads)},
                    summary=f"Move files in {downloads} into extension folders (records undo batch)",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Moves files into subfolders; undo batch stored locally",),
                ),
            ],
        )

    def _undo_organise_plan(self, goal: str) -> Plan:
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale="Reverse the most recent organise move batch recorded in local memory.",
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="undo_last_organise",
                    args={},
                    summary="Undo the last organise move batch",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Moves files back to their prior locations",),
                ),
            ],
        )

    def _copy_move_plan(self, goal: str) -> Plan:
        operation, source, destination = self._copy_move_parts_from_goal(goal)
        apply_action = "move_file" if operation == "move" else "copy_file"
        verb = "Move" if operation == "move" else "Copy"
        undo_note = (
            " A move is recorded in the organise undo journal so 'undo last move' can reverse it."
            if operation == "move"
            else " Copy is not auto-undone because that would delete the new file."
        )
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                f"{verb} journey — preview the source and destination, then {operation} the file."
                f"{undo_note} Overwrite is refused. Does not walk the Windows directory."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="preview_copy_move",
                    args={
                        "source": source,
                        "destination": destination,
                        "operation": operation,
                    },
                    summary=f"Preview {operation} of {source} to {destination}",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads file metadata; no copy or move yet",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action=apply_action,
                    args={"source": source, "destination": destination},
                    summary=f"{verb} {source} to {destination}",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=(
                        "Moves the file and records an undo batch"
                        if operation == "move"
                        else "Creates a new file at the destination"
                    ),
                ),
            ],
        )

    def _copy_move_parts_from_goal(self, goal: str) -> tuple[str, str, str]:
        lower = goal.lower()
        operation = "move" if re.search(r"\bmove\b", lower) and "copy" not in lower else "copy"
        match = re.search(
            r"\b(?:copy|move)\s+(?:the\s+file\s+)?(.+?)\s+to\s+(.+)$",
            goal,
            flags=re.I,
        )
        source_token = match.group(1).strip().strip("\"'") if match else ""
        dest_token = match.group(2).strip().strip("\"'") if match else ""
        source_token = re.sub(r"^(?:file|the file)\s+", "", source_token, flags=re.I).strip()
        dest_token = re.sub(r"^(?:folder|the folder|directory|my)\s+", "", dest_token, flags=re.I).strip()
        return operation, self._resolve_transfer_path(source_token, is_source=True), self._resolve_transfer_path(
            dest_token, is_source=False
        )

    def _old_downloads_plan(self, goal: str) -> Plan:
        downloads = self._downloads_dir()
        days = self._older_than_days_from_goal(goal)
        lower = goal.lower()
        delete = any(word in lower for word in ("empty", "clear", "delete", "purge", "clean", "remove"))
        steps = [
            ToolStep(
                id=new_id("step_"),
                adapter="files",
                action="inspect_old_files",
                args={"path": str(downloads), "older_than_days": days, "max_results": 200},
                summary=f"Read-only: list top-level files in {downloads} older than {days} days",
                sensitivity=Sensitivity.READ,
                side_effects=("Reads names, sizes, and modification times",),
            )
        ]
        rationale = (
            "Old-Downloads journey — inspect first. "
            f"Deleting top-level files older than {days} days needs a fresh hard confirmation. "
            "Subfolders are never removed."
        )
        if delete:
            steps.append(
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="delete_old_files",
                    args={"path": str(downloads), "older_than_days": days, "max_results": 200},
                    summary=f"Delete top-level files in Downloads older than {days} days",
                    sensitivity=Sensitivity.DESTRUCTIVE,
                    side_effects=("Permanently deletes matching top-level files",),
                )
            )
        else:
            rationale = (
                "Old-Downloads journey — read-only listing of top-level files older than "
                f"{days} days. Ask to delete them for a separate hard-confirm plan."
            )
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=rationale,
            steps=steps,
        )

    @staticmethod
    def _older_than_days_from_goal(goal: str) -> int:
        match = re.search(r"older than\s+(\d+)\s+days?", goal, flags=re.I)
        if not match:
            match = re.search(r"(\d+)\s+days?\s+old", goal, flags=re.I)
        if not match:
            match = re.search(r"older than\s+(\d+)", goal, flags=re.I)
        if match:
            return max(1, min(int(match.group(1)), 3650))
        return 30

    def _resolve_transfer_path(self, token: str, *, is_source: bool) -> str:
        raw = (token or "").strip().strip("\"'")
        lower = raw.lower().rstrip("\\/")
        named = {
            "downloads": self._downloads_dir(),
            "download": self._downloads_dir(),
            "documents": self._documents_dir(),
            "docs": self._documents_dir(),
            "desktop": Path.home() / "Desktop",
            "notes": self._notes_dir(),
        }
        if lower in named:
            return str(named[lower])
        if not raw:
            return str(self._downloads_dir() if is_source else self._documents_dir())
        if re.match(r"^[A-Za-z]:\\", raw) or raw.startswith(("~", "/", "\\")):
            if raw.startswith("~"):
                return str(Path.home() / raw[2:].lstrip("\\/"))
            return raw
        if is_source:
            return str(self._downloads_dir() / raw)
        return str(self._documents_dir() / raw)

    def _save_note_plan(self, goal: str) -> Plan:
        notes_root = self._notes_dir()
        body = self._note_body_from_goal(goal)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        note_path = notes_root / f"note-{stamp}.txt"
        content = f"{body}\n"
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Save-note journey — write one local text file after ensuring the notes folder. "
                "Nothing is uploaded; overwrite is avoided with a timestamped filename."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="ensure_directory",
                    args={"path": str(notes_root)},
                    summary=f"Ensure notes folder exists at {notes_root}",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("May create a directory",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="write_text",
                    args={"path": str(note_path), "content": content},
                    summary=f"Write {note_path.name} in the notes folder",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Creates a new local text file",),
                ),
            ],
        )

    @staticmethod
    def _note_body_from_goal(goal: str) -> str:
        text = goal.strip()
        text = re.sub(
            r"^(?:save a note|write a note|add a note|leave a note|save note|jot down)\s*"
            r"(?:about|that|:)?\s*",
            "",
            text,
            count=1,
            flags=re.I,
        )
        return text.strip() or "Empty note from Arbora."

    def _folder_path_from_goal(self, goal: str) -> str:
        lower = goal.lower()
        path_match = re.search(r"(?:in|at)\s+([A-Za-z]:\\[^\"]+|~[/\\][^\"]+|[/\\][^\"]+)", goal)
        if path_match:
            path = path_match.group(1)
            if path.startswith("~"):
                return str(Path.home() / path[2:].lstrip("\\/"))
            return path
        if "desktop" in lower:
            return str(Path.home() / "Desktop")
        if re.search(r"\btemp\b", lower) and "temperature" not in lower:
            return str(_user_temp_dir())
        if re.search(r"\bdocuments?\b", lower) or re.search(r"\bdocs\b", lower):
            return str(self._documents_dir())
        return str(self._downloads_dir())

    @staticmethod
    def _search_pattern_from_goal(goal: str) -> str:
        match = re.search(
            r"(?:find|locate|search for)\s+(?:files?\s+)?(?:named\s+|called\s+)?(.+?)(?:\s+in\s+|\s+under\s+|$)",
            goal,
            flags=re.IGNORECASE,
        )
        if not match:
            return "*"
        token = match.group(1).strip().strip("\"'")
        token = re.sub(r"\s+files?$", "", token, flags=re.IGNORECASE).strip()
        if not token or token.lower() in {"file", "a file", "the file"}:
            return "*"
        return token

    def _open_explorer_plan(self, goal: str) -> Plan:
        path = self._folder_path_from_goal(goal)
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Open-folder journey — list the folder, then open it in Explorer. "
                "Opens a window on your desktop; does not move or delete files."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="list_directory",
                    args={"path": path},
                    summary=f"List files in {path}",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads directory listing",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="open_in_explorer",
                    args={"path": path},
                    summary=f"Open {path} in File Explorer",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Opens a File Explorer window",),
                ),
            ],
        )

    def _recycle_bin_plan(self, goal: str) -> Plan:
        lower = goal.lower()
        empty = any(word in lower for word in ("empty", "clear", "delete", "purge"))
        steps = [
            ToolStep(
                id=new_id("step_"),
                adapter="files",
                action="inspect_recycle_bin",
                args={},
                summary="Read-only: list Recycle Bin item names",
                sensitivity=Sensitivity.READ,
                side_effects=("Reads Recycle Bin names via Shell.Application",),
            )
        ]
        rationale = (
            "Recycle Bin journey — inspect first. "
            "Emptying permanently removes those items and needs a fresh hard confirmation."
        )
        if empty:
            steps.append(
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="empty_recycle_bin",
                    args={},
                    summary="Empty the Recycle Bin (permanent)",
                    sensitivity=Sensitivity.DESTRUCTIVE,
                    side_effects=("Permanently deletes Recycle Bin contents",),
                )
            )
        else:
            rationale = "Recycle Bin journey — read-only listing of item names. Ask to empty it for a separate hard-confirm plan."
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=rationale,
            steps=steps,
        )

    def _find_files_plan(self, goal: str) -> Plan:
        path = self._folder_path_from_goal(goal)
        pattern = self._search_pattern_from_goal(goal)
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Find-files journey — read-only name search with a depth cap. "
                "Does not open, move, or delete files."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="search_by_name",
                    args={"path": path, "pattern": pattern, "max_depth": 3, "max_results": 50},
                    summary=f"Search {path} for names matching {pattern}",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads file names under the folder",),
                )
            ],
        )

    def _temp_plan(self, goal: str) -> Plan:
        lower = goal.lower()
        clean = any(word in lower for word in ("empty", "clear", "delete", "purge", "clean"))
        steps = [
            ToolStep(
                id=new_id("step_"),
                adapter="files",
                action="inspect_user_temp",
                args={},
                summary="Read-only: list top-level files in the user TEMP folder",
                sensitivity=Sensitivity.READ,
                side_effects=("Reads names and sizes in %TEMP%",),
            )
        ]
        rationale = (
            "User TEMP journey — inspect first. "
            "Cleaning deletes top-level files only (directories stay) and needs a fresh hard confirmation."
        )
        if clean:
            steps.append(
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="clean_user_temp",
                    args={},
                    summary="Delete top-level files in user TEMP (directories kept)",
                    sensitivity=Sensitivity.DESTRUCTIVE,
                    side_effects=("Permanently deletes files in %TEMP%",),
                )
            )
        else:
            rationale = (
                "User TEMP journey — read-only listing of top-level files. "
                "Ask to clean temp for a separate hard-confirm plan."
            )
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=rationale,
            steps=steps,
        )

    def _close_window_plan(self, goal: str) -> Plan:
        title = self._close_window_title_from_goal(goal)
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Close-window journey — send WM_CLOSE to the first matching titled window. "
                "Does not force-kill (no taskkill / Stop-Process). "
                "Apps may still prompt to save. Still requires broker approval."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="close_window",
                    args={"title_contains": title},
                    summary=f"Close the window matching '{title}' with WM_CLOSE",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Sends a close request to one window; does not force-kill",),
                )
            ],
        )

    @staticmethod
    def _close_window_title_from_goal(goal: str) -> str:
        text = goal.strip()
        match = re.search(
            r"close\s+window\s+(?:titled|named|called)\s+(.+)$",
            text,
            flags=re.I,
        )
        if match:
            return match.group(1).strip().strip("\"'")
        match = re.search(r"close\s+(?:the\s+)?(.+?)\s+window\b", text, flags=re.I)
        if match:
            return match.group(1).strip().strip("\"'")
        match = re.search(r"close\s+(?:the\s+)?(.+)$", text, flags=re.I)
        if match:
            return match.group(1).strip().strip("\"'")
        return text

    def _open_in_browser_plan(self, goal: str) -> Plan:
        url = self._http_url_from_goal(goal)
        alias = self._app_alias_from_goal(goal.lower()) or "edge"
        if alias not in {"chrome", "edge", "firefox"}:
            alias = "edge"
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Open-URL journey — Start-Process the installed Chrome, Edge, or Firefox "
                "with one http(s) URL. Does not use Playwright. Still requires broker approval."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="open_in_browser",
                    args={"url": url, "name": alias},
                    summary=f"Open {url} in installed {alias}",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Starts the installed browser with one URL argument",),
                )
            ],
        )

    @staticmethod
    def _http_url_from_goal(goal: str) -> str:
        match = re.search(r"https?://[^\s\"'<>]+", goal, flags=re.I)
        if not match:
            return ""
        return match.group(0).rstrip(".,);]")

    def _launch_app_plan(self, goal: str) -> Plan:
        alias = self._app_alias_from_goal(goal.lower()) or "notepad"
        focus = {
            "chrome": "Chrome",
            "edge": "Edge",
            "firefox": "Firefox",
            "vscode": "Visual Studio Code",
            "discord": "Discord",
            "spotify": "Spotify",
            "wt": "Terminal",
            "notepad": "Notepad",
            "calc": "Calculator",
            "slack": "Slack",
        }.get(alias, alias)
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Launch-app journey — start a known desktop app by alias. "
                "Uses your installed Chrome/Edge/VS Code if present; does not drive a browser session."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="launch_app",
                    args={"name": alias},
                    summary=f"Launch {alias}",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Starts a process",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="focus_window",
                    args={"title_contains": focus},
                    summary=f"Focus the {focus} window if it is open",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Brings an existing window to the foreground",),
                ),
            ],
        )

    def _screenshot_plan(self, goal: str) -> Plan:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        folder = self._notes_dir() / "screenshots"
        path = folder / f"screenshot-{stamp}.png"
        window_title = self._screenshot_window_from_goal(goal)
        capture_args: dict[str, Any] = {"path": str(path)}
        if window_title:
            capture_args["window_title"] = window_title
        capture_summary = (
            f"Capture the '{window_title}' window to {path.name}"
            if window_title
            else f"Capture the primary screen to {path.name}"
        )
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Screenshot journey — write one PNG under the notes/screenshots folder. "
                "Still requires broker approval. Does not upload the image."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="ensure_directory",
                    args={"path": str(folder)},
                    summary=f"Ensure screenshots folder exists at {folder}",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("May create a directory",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="capture_screenshot",
                    args=capture_args,
                    summary=capture_summary,
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Writes a PNG image on disk",),
                ),
            ],
        )

    @staticmethod
    def _screenshot_window_from_goal(goal: str) -> str:
        match = re.search(
            r"(?:of|named|called|window)\s+(?:the\s+)?(.+?)(?:\s+window)?$",
            goal.strip(),
            flags=re.I,
        )
        if not match:
            return ""
        token = match.group(1).strip().strip("\"'")
        token = re.sub(r"\bwindow\b", "", token, flags=re.I).strip()
        if token.lower() in {"screen", "desktop", "primary screen", "the screen", "my screen"}:
            return ""
        return token

    def _recent_files_plan(self, goal: str) -> Plan:
        path = self._folder_path_from_goal(goal)
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Recent-files journey — read-only newest-first listing with a depth cap. "
                "Does not open, move, or delete files."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="list_recent",
                    args={"path": path, "max_depth": 2, "max_results": 20},
                    summary=f"List newest files in {path}",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads file names, sizes, and modification times",),
                )
            ],
        )

    def _save_clipboard_plan(self, goal: str) -> Plan:
        notes_root = self._notes_dir()
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        note_path = notes_root / f"clipboard-{stamp}.txt"
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Save-clipboard journey — write clipboard text to a timestamped file in the notes folder. "
                "Empty, image, file-list, and password/token-like clipboard contents are refused. "
                "Still requires broker approval."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="ensure_directory",
                    args={"path": str(notes_root)},
                    summary=f"Ensure notes folder exists at {notes_root}",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("May create a directory",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="save_clipboard_text",
                    args={"path": str(note_path)},
                    summary=f"Save clipboard text to {note_path.name}",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Reads the clipboard and may create a local text file",),
                ),
            ],
        )

    def _clipboard_plan(self, goal: str) -> Plan:
        lower = goal.lower()
        reveal = any(
            word in lower
            for word in ("show", "reveal", "read", "paste", "contents", "text")
        )
        summary = (
            "Show a short clipboard text preview (secrets still withheld)"
            if reveal
            else "Inspect clipboard type and length (content withheld)"
        )
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Clipboard journey — read-only inspect. "
                "Default is type and length only. A short preview needs an explicit show request, "
                "and password/token-like text is still withheld."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="inspect_clipboard",
                    args={"reveal": reveal},
                    summary=summary,
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads the Windows clipboard",),
                )
            ],
        )

    def _spoken_confirmation_plan(self, goal: str) -> Plan:
        spoken = sanitize_speech_text(self._spoken_text_from_goal(goal))
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Spoken confirmation journey — read back a short phrase through the speakers. "
                "Does not listen on the microphone. Still requires broker approval."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="desktop",
                    action="speak_text",
                    args={"text": spoken},
                    summary="Speak a short confirmation read-back",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Plays speech through the default Windows voice",),
                )
            ],
        )

    def _maybe_add_spoken_confirmation(self, plan: Plan) -> Plan:
        if not self._spoken_confirmations:
            return plan
        if any(step.action == "speak_text" for step in plan.steps):
            return plan
        spoken = sanitize_speech_text(self._spoken_confirmation_text(plan))
        plan.steps.insert(
            0,
            ToolStep(
                id=new_id("step_"),
                adapter="desktop",
                action="speak_text",
                args={"text": spoken},
                summary="Speak a short read-back of this plan",
                sensitivity=Sensitivity.MUTATE,
                side_effects=("Plays speech through the default Windows voice",),
            ),
        )
        return plan

    @staticmethod
    def _spoken_confirmation_text(plan: Plan) -> str:
        parts = [f"Plan for {plan.goal}."]
        for index, step in enumerate(plan.steps, start=1):
            parts.append(f"Step {index}: {step.summary}.")
            if step.requires_hard_confirmation():
                parts.append("This step needs hard confirmation.")
        return " ".join(parts)

    @staticmethod
    def _spoken_text_from_goal(goal: str) -> str:
        match = re.search(
            r"(?:read (?:this|that|it) back|read back|speak(?: this| that| confirmation)?|"
            r"say this|spoken confirmation|read the plan|speak the plan)\s*[:\-]?\s*(.*)$",
            goal,
            flags=re.IGNORECASE,
        )
        if match:
            token = match.group(1).strip().strip("\"'")
            if token:
                return token
        return "Please review the Arbora plan on screen before it runs."

    def _list_files_plan(self, goal: str) -> Plan:
        path = self._folder_path_from_goal(goal)
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale="Simple file listing request.",
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="list_directory",
                    args={"path": path},
                    summary=f"List files in {path}",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads directory listing",),
                ),
            ],
        )

    def _run_tests_plan(self, goal: str) -> Plan:
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Pytest journey — run the test suite in the current directory. "
                "1) Confirm pytest is importable. 2) Run python -m pytest. "
                "Does not commit, push, or install packages."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="terminal",
                    action="run_powershell",
                    args={
                        "command": "python -m pytest --version 2>&1 | Out-String",
                        "timeout_seconds": 30,
                    },
                    summary="Check that python -m pytest is available",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Runs a version query in PowerShell",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="terminal",
                    action="run_powershell",
                    args={
                        "command": "python -m pytest -q --tb=short 2>&1 | Out-String",
                        "timeout_seconds": 180,
                    },
                    summary="Run pytest in the current directory (may write .pytest_cache)",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Executes the project test suite",),
                ),
            ],
        )

    def _terminal_plan(self, goal: str) -> Plan:
        command_match = re.search(r"(?:run|execute)\s+[`'\"]?(.+?)[`'\"]?$", goal, re.I)
        command = command_match.group(1).strip() if command_match else "Get-Date | Out-String"
        sensitivity = Sensitivity.MUTATE
        if powershell_is_destructive(command):
            sensitivity = Sensitivity.DESTRUCTIVE
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale="Terminal request captured as an explicit PowerShell step.",
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="terminal",
                    action="run_powershell",
                    args={"command": command, "timeout_seconds": 60},
                    summary=f"Run PowerShell: {command}",
                    sensitivity=sensitivity,
                    side_effects=("Executes a shell command with captured output",),
                ),
            ],
        )

    def _research_plan(self, goal: str) -> Plan:
        url_match = re.search(r"https?://[^\s\"']+", goal)
        url = url_match.group(0) if url_match else "https://example.com"
        topic = re.sub(r"https?://[^\s\"']+", "", goal, count=1).strip(" -:")
        topic = re.sub(
            r"^(research|look up|lookup|summarise|summarize|save a brief about|save brief about|read)\s+",
            "",
            topic,
            flags=re.I,
        ).strip() or "web page"
        brief_name = re.sub(r"[^\w\-]+", "-", topic.lower()).strip("-")[:48] or "brief"
        briefs_root = self._briefs_root or Path.home() / "ArboraBriefs"
        brief_path = str(briefs_root / f"{brief_name}.md")
        snapshot_path = str(briefs_root / f"{brief_name}-snapshot.png")
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=(
                "Web research journey — page text is untrusted data and is never executed as tools. "
                "1) Open URL. 2) Title + excerpt + links. 3) Save a page snapshot. "
                "4) Save a local cited brief. 5) Close browser."
            ),
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="ensure_directory",
                    args={"path": str(briefs_root)},
                    summary="Ensure ArboraBriefs folder exists",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("May create a directory under your home folder",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="browser",
                    action="open_url",
                    args={"url": url, "headed": False},
                    summary=f"Open {url} in headless Chromium",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Launches Playwright Chromium and navigates to URL",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="browser",
                    action="get_title",
                    args={},
                    summary="Read page title",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads DOM title",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="browser",
                    action="extract_text",
                    args={},
                    summary="Extract main visible text (truncated, untrusted)",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads page text as untrusted data",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="browser",
                    action="extract_links",
                    args={},
                    summary="Extract http(s) links from the page",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads anchor hrefs",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="browser",
                    action="snapshot",
                    args={"path": snapshot_path, "full_page": False},
                    summary=f"Save page snapshot to {brief_name}-snapshot.png",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Writes a PNG screenshot under ArboraBriefs",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="browser",
                    action="save_brief",
                    args={"path": brief_path, "topic": topic},
                    summary=f"Save research brief to {brief_path}",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Writes a markdown file under ArboraBriefs",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="browser",
                    action="close",
                    args={},
                    summary="Close browser session",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Closes Playwright Chromium",),
                ),
            ],
        )

    @staticmethod
    def _looks_like_spoken_confirmation(lower: str) -> bool:
        return any(
            phrase in lower
            for phrase in (
                "read this back",
                "read that back",
                "read it back",
                "read back",
                "speak confirmation",
                "spoken confirmation",
                "speak this",
                "say this",
                "read the plan",
                "speak the plan",
            )
        )

    @staticmethod
    def _looks_like_workday_start(lower: str) -> bool:
        return any(
            phrase in lower
            for phrase in (
                "start my workday",
                "start workday",
                "begin my day",
                "begin workday",
                "open my work setup",
                "morning setup",
                "kick off my day",
                "start my day",
            )
        )

    @staticmethod
    def _looks_like_workday_shutdown(lower: str) -> bool:
        return any(
            phrase in lower
            for phrase in (
                "end my workday",
                "shutdown workday",
                "finish my day",
                "wrap up work",
                "end of day",
                "close out my day",
                "shut down for the day",
            )
        )

    @staticmethod
    def _drive_root_from_goal(goal: str) -> str:
        match = re.search(r"\b([a-zA-Z]):(?:\\|/)?", goal)
        if match:
            return f"{match.group(1).upper()}:\\"
        match = re.search(r"\b([a-zA-Z])\s+drive\b", goal, re.I)
        if match:
            return f"{match.group(1).upper()}:\\"
        return "C:\\"

    @staticmethod
    def _looks_like_largest_folders(lower: str) -> bool:
        phrases = (
            "largest folder",
            "biggest folder",
            "which folder uses",
            "what folder is using",
            "what folderis using",
            "folder using the most",
            "folder that uses the most",
            "folders using the most",
            "what's taking up space",
            "whats taking up space",
            "taking up the most space",
            "using the most storage",
            "uses the most storage",
            "using the most space",
            "uses the most disk",
            "what's using the most space",
            "whats using the most space",
            "what is using the most storage",
        )
        if any(phrase in lower for phrase in phrases):
            return True
        folderish = any(word in lower for word in ("folder", "directory"))
        sizeish = any(
            word in lower
            for word in ("storage", "disk space", "disk usage", "largest", "biggest")
        )
        return folderish and sizeish

    @staticmethod
    def _looks_like_network_status(lower: str) -> bool:
        if any(word in lower for word in ("diagnos", "troubleshoot", "broken", "repair", "fix")):
            return False
        return any(
            phrase in lower
            for phrase in (
                "wifi status",
                "wi-fi status",
                "wireless status",
                "network adapter",
                "network adapters",
                "what's my ip",
                "whats my ip",
                "what is my ip",
                "my ip address",
                "ip configuration",
                "ip config",
                "ipconfig",
                "inspect network",
                "network status",
                "wifi adapters",
                "connection profile",
            )
        )

    @staticmethod
    def _looks_like_battery_status(lower: str) -> bool:
        if any(word in lower for word in ("diagnos", "troubleshoot", "broken", "repair", "fix")):
            return False
        return any(
            phrase in lower
            for phrase in (
                "battery status",
                "battery level",
                "battery percent",
                "battery percentage",
                "battery remaining",
                "power status",
                "power supply",
                "on battery",
                "inspect battery",
                "laptop battery",
                "how much battery",
                "charging status",
                "is my laptop charging",
            )
        )

    @staticmethod
    def _looks_like_printer_status(lower: str) -> bool:
        if any(word in lower for word in ("diagnos", "troubleshoot", "broken", "repair", "fix")):
            return False
        if not re.search(r"\bprinters?\b", lower):
            return False
        return any(
            phrase in lower
            for phrase in (
                "printer status",
                "printers status",
                "default printer",
                "list printers",
                "list printer",
                "what printers",
                "what's my printer",
                "whats my printer",
                "what is my printer",
                "inspect printer",
                "installed printers",
                "installed printer",
                "my printers",
                "my printer",
            )
        )

    @staticmethod
    def _looks_like_startup_apps(lower: str) -> bool:
        if any(word in lower for word in ("diagnos", "troubleshoot", "broken", "repair", "fix")):
            return False
        if "workday" in lower:
            return False
        return any(
            phrase in lower
            for phrase in (
                "startup apps",
                "startup app",
                "startup programs",
                "startup program",
                "startup items",
                "inspect startup",
                "list startup",
                "startup folder",
                "what starts with windows",
                "what runs at startup",
                "what runs on startup",
                "apps that start with windows",
                "programs that start with windows",
            )
        )

    @staticmethod
    def _looks_like_default_browser(lower: str) -> bool:
        if any(word in lower for word in ("diagnos", "troubleshoot", "broken", "repair", "fix")):
            return False
        if re.search(r"https?://", lower):
            return False
        if "printer" in lower:
            return False
        return any(
            phrase in lower
            for phrase in (
                "default browser",
                "default web browser",
                "inspect default browser",
                "which browser",
                "what browser",
                "what's my browser",
                "whats my browser",
                "what is my browser",
                "my default browser",
            )
        )

    @staticmethod
    def _looks_like_display_status(lower: str) -> bool:
        if any(word in lower for word in ("diagnos", "troubleshoot", "broken", "repair", "fix")):
            return False
        if any(
            word in lower
            for word in ("screenshot", "screen shot", "screen-shot", "capture", "snapshot", "wallpaper")
        ):
            return False
        return any(
            phrase in lower
            for phrase in (
                "screen resolution",
                "display resolution",
                "monitor resolution",
                "what's my resolution",
                "whats my resolution",
                "what is my resolution",
                "inspect display",
                "inspect displays",
                "list displays",
                "list monitors",
                "how many monitors",
                "how many displays",
                "display status",
                "attached displays",
                "attached monitors",
                "my monitors",
                "my displays",
                "what's my screen size",
                "whats my screen size",
                "monitor setup",
            )
        )

    @staticmethod
    def _looks_like_windows_update(lower: str) -> bool:
        if any(word in lower for word in ("diagnos", "troubleshoot", "broken", "repair", "fix")):
            return False
        if any(
            phrase in lower
            for phrase in (
                "install update",
                "install updates",
                "install windows update",
                "download update",
                "download updates",
                "download windows update",
                "check for update",
                "check for updates",
            )
        ):
            return False
        return any(
            phrase in lower
            for phrase in (
                "windows update",
                "last windows update",
                "when were updates installed",
                "when was the last update installed",
                "last installed update",
                "inspect windows update",
                "when did windows last update",
                "latest windows update",
                "last hotfix",
                "hotfix install date",
                "last update installed",
            )
        )

    @staticmethod
    def _looks_like_diagnostic(lower: str) -> bool:
        return any(
            phrase in lower
            for phrase in (
                "diagnos",
                "troubleshoot",
                "disk space",
                "low disk",
                "why won't",
                "why wont",
                "pc issue",
                "computer problem",
                "network feels",
                "wifi broken",
                "wifi won't",
                "memory usage",
                "what's using",
                "whats using",
                "slow pc",
                "slow computer",
            )
        )

    @staticmethod
    def _looks_like_dev_setup(lower: str) -> bool:
        return any(
            phrase in lower
            for phrase in (
                "set up a project",
                "setup project",
                "set up the project",
                "dev setup",
                "toolchain",
                "clone this repo",
                "create a venv",
                "install dependencies",
                "install deps",
                "project setup",
            )
        )

    @staticmethod
    def _looks_like_organise_downloads(lower: str) -> bool:
        return "download" in lower and any(
            w in lower for w in ("organis", "organiz", "sort my", "sort the", "filing", "file my")
        )

    @staticmethod
    def _looks_like_undo_organise(lower: str) -> bool:
        return any(
            phrase in lower
            for phrase in (
                "undo last organise",
                "undo organise",
                "reverse organise",
                "undo file moves",
                "undo last file",
                "undo last move",
                "undo the last move",
            )
        )

    @staticmethod
    def _looks_like_copy_move(lower: str) -> bool:
        if "clipboard" in lower or "window" in lower or "recycle" in lower:
            return False
        if "organis" in lower or "organiz" in lower:
            return False
        if not re.search(r"\b(copy|move)\b", lower):
            return False
        if " to " not in lower:
            return False
        return bool(
            re.search(
                r"\.(pdf|txt|docx?|xlsx?|png|jpe?g|zip|md|csv)\b",
                lower,
            )
            or "file" in lower
            or ":\\" in lower
            or "~/" in lower
        )

    @staticmethod
    def _looks_like_old_downloads(lower: str) -> bool:
        if "download" not in lower:
            return False
        if any(
            word in lower
            for word in ("organis", "organiz", "recent", "latest", "newest", "recycle", "clipboard")
        ):
            return False
        return any(
            phrase in lower
            for phrase in (
                "old download",
                "old files in download",
                "old in download",
                "downloads older",
                "download older",
                "older than",
                "delete old",
                "empty old",
                "clean old",
                "remove old",
                "purge old",
                "files older",
            )
        )

    @staticmethod
    def _looks_like_save_note(lower: str) -> bool:
        return any(
            phrase in lower
            for phrase in (
                "save a note",
                "write a note",
                "add a note",
                "leave a note",
                "save note",
                "jot down",
            )
        )

    @staticmethod
    def _looks_like_open_explorer(lower: str) -> bool:
        return any(
            phrase in lower
            for phrase in (
                "in explorer",
                "in file explorer",
                "open folder",
                "open explorer",
                "show in explorer",
                "reveal in explorer",
            )
        )

    @staticmethod
    def _looks_like_recycle_bin(lower: str) -> bool:
        return "recycle bin" in lower or "recyclebin" in lower

    @staticmethod
    def _looks_like_find_files(lower: str) -> bool:
        if "research" in lower or "recycle" in lower:
            return False
        if "search google" in lower or "search the web" in lower:
            return False
        if lower.startswith("find ") and " in " in lower:
            return True
        return any(
            phrase in lower
            for phrase in (
                "find file",
                "find files",
                "search for",
                "locate file",
                "locate files",
            )
        )

    @staticmethod
    def _looks_like_temp(lower: str) -> bool:
        if "temperature" in lower:
            return False
        if re.search(r"\bin temp\b", lower):
            return True
        return any(
            phrase in lower
            for phrase in (
                "temp folder",
                "temporary files",
                "windows temp",
                "user temp",
                "clean temp",
                "empty temp",
                "clear temp",
                "what's in temp",
                "whats in temp",
                "inspect temp",
            )
        )

    @staticmethod
    def _app_alias_from_goal(lower: str) -> str | None:
        phrases = (
            ("visual studio code", "vscode"),
            ("google chrome", "chrome"),
            ("microsoft edge", "edge"),
            ("windows terminal", "wt"),
            ("chrome", "chrome"),
            ("msedge", "edge"),
            ("firefox", "firefox"),
            ("vscode", "vscode"),
            ("discord", "discord"),
            ("spotify", "spotify"),
            ("notepad", "notepad"),
            ("calculator", "calc"),
            ("slack", "slack"),
            ("edge", "edge"),
        )
        for phrase, alias in phrases:
            if phrase in lower:
                return alias
        if re.search(r"\b(open|launch|start)\s+code\b", lower):
            return "vscode"
        return None

    @staticmethod
    def _looks_like_close_window(lower: str) -> bool:
        if any(
            phrase in lower
            for phrase in (
                "workday",
                "recycle",
                "close out",
                "end of day",
                "for the day",
                "my day",
            )
        ):
            return False
        if re.search(r"\bclose\s+window\s+(titled|named|called)\s+\S", lower):
            return True
        if re.search(r"\bclose\s+(the\s+)?.+\s+window\b", lower):
            return True
        return bool(
            re.search(
                r"\bclose\s+(the\s+)?(notepad|chrome|edge|firefox|discord|spotify|"
                r"calculator|calc|code|vscode|slack|paint)\b",
                lower,
            )
        )

    @staticmethod
    def _looks_like_open_in_browser(lower: str) -> bool:
        if not re.search(r"https?://", lower):
            return False
        if any(
            word in lower
            for word in ("research", "brief", "summarise", "summarize", "snapshot", "extract")
        ):
            return False
        if not re.search(r"\b(open|launch)\b", lower):
            return False
        return bool(re.search(r"\b(chrome|msedge|firefox|edge)\b", lower))

    @staticmethod
    def _looks_like_launch_app(lower: str) -> bool:
        if any(
            phrase in lower
            for phrase in (
                "in explorer",
                "open folder",
                "http://",
                "https://",
                "recycle",
                "workday",
            )
        ):
            return False
        if not re.search(r"\b(open|launch|start)\b", lower):
            return False
        return GoalPlanner._app_alias_from_goal(lower) is not None

    @staticmethod
    def _looks_like_save_clipboard(lower: str) -> bool:
        if "clipboard" not in lower:
            return False
        return any(
            phrase in lower
            for phrase in (
                "save clipboard",
                "save the clipboard",
                "save my clipboard",
                "clipboard to notes",
                "clipboard to a note",
                "clipboard into a note",
                "clipboard as a note",
                "paste clipboard",
                "write clipboard",
                "copy clipboard",
                "note from clipboard",
            )
        )

    @staticmethod
    def _looks_like_clipboard(lower: str) -> bool:
        return "clipboard" in lower

    @staticmethod
    def _looks_like_screenshot(lower: str) -> bool:
        if any(
            word in lower
            for word in ("http://", "https://", "research", "brief", "web page", "browser", "clipboard")
        ):
            return False
        return any(
            phrase in lower
            for phrase in (
                "screenshot",
                "screen shot",
                "screen-shot",
                "capture the screen",
                "capture my screen",
                "capture the window",
                "capture window",
                "snapshot the screen",
                "snapshot the window",
                "take a snapshot of the screen",
            )
        )

    @staticmethod
    def _looks_like_recent_files(lower: str) -> bool:
        if any(word in lower for word in ("history", "goal", "recycle", "clipboard", "temp")):
            return False
        return any(
            phrase in lower
            for phrase in (
                "recent files",
                "recent downloads",
                "recent documents",
                "recent docs",
                "latest files",
                "latest downloads",
                "latest documents",
                "newest files",
                "newest downloads",
                "newest documents",
                "what did i download",
                "recently downloaded",
                "list recent",
                "show recent",
            )
        )

    @staticmethod
    def _looks_like_list_files(lower: str) -> bool:
        if "clipboard" in lower or "recent" in lower or "latest" in lower:
            return False
        return any(phrase in lower for phrase in ("list files", "show files", "what's in", "whats in"))

    @staticmethod
    def _looks_like_research(lower: str, original: str) -> bool:
        if re.search(r"https?://", original):
            return any(
                phrase in lower
                for phrase in (
                    "research",
                    "look up",
                    "lookup",
                    "summarise",
                    "summarize",
                    "brief",
                    "read this",
                    "open ",
                )
            ) or lower.startswith("http")
        return any(
            phrase in lower
            for phrase in (
                "research ",
                "look up ",
                "save a brief",
                "web brief",
                "summarise the page",
                "summarize the page",
            )
        )

    @staticmethod
    def _looks_like_run_tests(lower: str) -> bool:
        return any(
            phrase in lower
            for phrase in (
                "run pytest",
                "run the tests",
                "run tests",
                "pytest pack",
                "run unit tests",
                "run the test suite",
            )
        )

    @staticmethod
    def _looks_like_terminal(lower: str) -> bool:
        return lower.startswith("run ") or lower.startswith("execute ")
