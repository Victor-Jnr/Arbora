"""Goal planner — turns natural-language goals into inspectable tool plans.

Known journeys use deterministic templates. Unmatched goals may use a model
provider (e.g. local Ollama) to propose a JSON plan, which is validated before
returning. Models propose; the permission broker still disposes.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from arbora.core.tool_catalog import ALLOWED_ACTIONS
from arbora.core.types import Plan, Sensitivity, ToolStep, new_id
from arbora.providers.base import ModelProvider
from arbora.workflows.packs import match_workflow_pack

SENSITIVITY_VALUES = {item.value: item for item in Sensitivity}

DRIVE_SIZE_WALK_TIMEOUT_SECONDS = 300


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
    ) -> None:
        self._provider = provider
        self._workday_root = workday_root
        self._briefs_root = briefs_root
        self._projects_root = projects_root
        self._downloads_root = downloads_root
        self._notes_root = notes_root

    def _downloads_dir(self) -> Path:
        return self._downloads_root or Path.home() / "Downloads"

    def _notes_dir(self) -> Path:
        return self._notes_root or Path.home() / "ArboraNotes"

    def plan(self, goal: str) -> Plan:
        text = goal.strip()
        lower = text.lower()

        if self._looks_like_workday_start(lower):
            return self._workday_start_plan(text)
        if self._looks_like_workday_shutdown(lower):
            return self._workday_shutdown_plan(text)
        if self._looks_like_largest_folders(lower):
            return self._largest_folders_plan(text)
        if self._looks_like_diagnostic(lower):
            return self._diagnostic_plan(text)
        if self._looks_like_dev_setup(lower):
            return self._dev_setup_plan(text)
        if self._looks_like_organise_downloads(lower):
            return self._organise_downloads_plan(text)
        if self._looks_like_undo_organise(lower):
            return self._undo_organise_plan(text)
        if self._looks_like_save_note(lower):
            return self._save_note_plan(text)
        if self._looks_like_list_files(lower):
            return self._list_files_plan(text)
        if self._looks_like_research(lower, text):
            return self._research_plan(text)
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

    def _list_files_plan(self, goal: str) -> Plan:
        path_match = re.search(r"(?:in|at)\s+([A-Za-z]:\\[^\"]+|~[/\\][^\"]+|[/\\][^\"]+)", goal)
        path = path_match.group(1) if path_match else str(self._downloads_dir())
        if path.startswith("~"):
            path = str(Path.home() / path[2:].lstrip("\\/"))
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
    def _looks_like_list_files(lower: str) -> bool:
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
    def _looks_like_terminal(lower: str) -> bool:
        return lower.startswith("run ") or lower.startswith("execute ")
