"""Goal planner — turns natural-language goals into inspectable tool plans.

Stage 1 uses a deterministic stub so the plan → approve → execute loop
can be demonstrated without a model provider. Provider-backed planning
plugs in later behind the same Plan/ToolStep types.
"""

from __future__ import annotations

import re
from pathlib import Path

from arbora.core.types import Plan, Sensitivity, ToolStep, new_id
from arbora.providers.base import ModelProvider


class GoalPlanner:
    def __init__(self, provider: ModelProvider | None = None) -> None:
        self._provider = provider

    def plan(self, goal: str) -> Plan:
        text = goal.strip()
        lower = text.lower()

        if self._looks_like_workday_start(lower):
            return self._workday_start_plan(text)
        if self._looks_like_workday_shutdown(lower):
            return self._workday_shutdown_plan(text)
        if self._looks_like_diagnostic(lower):
            return self._diagnostic_plan(text)
        if self._looks_like_dev_setup(lower):
            return self._dev_setup_plan(text)
        if self._looks_like_organise_downloads(lower):
            return self._organise_downloads_plan(text)
        if self._looks_like_list_files(lower):
            return self._list_files_plan(text)
        if self._looks_like_terminal(lower):
            return self._terminal_plan(text)

        return Plan(
            id=new_id("plan_"),
            goal=text,
            rationale=(
                "No specialised journey matched. Offering a read-only context "
                "gathering plan. Refine the goal or connect a model provider for richer planning."
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
                    args={"path": str(Path.home() / "Downloads")},
                    summary="List files in Downloads",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads directory listing",),
                ),
            ],
        )

    def _workday_start_plan(self, goal: str) -> Plan:
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale="Workday setup journey: restore a focused desktop environment.",
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
                    adapter="desktop",
                    action="launch_app",
                    args={"name": "notepad"},
                    summary="Launch Notepad as a stand-in for your notes app",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Starts a process",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="ensure_directory",
                    args={"path": str(Path.home() / "ArboraWorkday")},
                    summary="Ensure today's work folder exists",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("May create a directory under your home folder",),
                ),
            ],
        )

    def _workday_shutdown_plan(self, goal: str) -> Plan:
        note_path = Path.home() / "ArboraWorkday" / "resume-tomorrow.txt"
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale="Workday shutdown journey: park context and close non-essential apps.",
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="write_text",
                    args={
                        "path": str(note_path),
                        "content": "Resume tomorrow: review open tasks and continue where you left off.\n",
                    },
                    summary=f"Write resume note to {note_path}",
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

    def _diagnostic_plan(self, goal: str) -> Plan:
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale="Troubleshooting journey: read-only diagnostics first, no silent repairs.",
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="terminal",
                    action="run_powershell",
                    args={
                        "command": "Get-PSDrive -PSProvider FileSystem | Select-Object Name, Used, Free | Format-Table | Out-String",
                        "timeout_seconds": 30,
                    },
                    summary="Read-only: report free disk space per drive",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Runs a read-only PowerShell query",),
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
                ToolStep(
                    id=new_id("step_"),
                    adapter="terminal",
                    action="run_powershell",
                    args={
                        "command": "Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 Name, Id, @{N='MB';E={[math]::Round($_.WorkingSet64/1MB,1)}} | Format-Table | Out-String",
                        "timeout_seconds": 30,
                    },
                    summary="Read-only: top processes by memory",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Runs a read-only PowerShell query",),
                ),
            ],
        )

    def _dev_setup_plan(self, goal: str) -> Plan:
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale="Developer assistance journey: inspect toolchain, then run approved setup commands.",
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="terminal",
                    action="run_powershell",
                    args={
                        "command": "python --version; git --version; node --version 2>$null; Write-Output 'toolchain check complete'",
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
                    args={"path": str(Path.cwd())},
                    summary="List files in the current working directory",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads directory listing",),
                ),
            ],
        )

    def _organise_downloads_plan(self, goal: str) -> Plan:
        downloads = Path.home() / "Downloads"
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale="File organisation journey: preview first; mutating moves need approval.",
            steps=[
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="list_directory",
                    args={"path": str(downloads)},
                    summary="Preview Downloads contents",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Reads directory listing",),
                ),
                ToolStep(
                    id=new_id("step_"),
                    adapter="files",
                    action="preview_organise",
                    args={"path": str(downloads)},
                    summary="Preview filing groups for Downloads (dry classification)",
                    sensitivity=Sensitivity.READ,
                    side_effects=("Classifies filenames in memory; no moves yet",),
                ),
            ],
        )

    def _list_files_plan(self, goal: str) -> Plan:
        path_match = re.search(r"(?:in|at)\s+([A-Za-z]:\\[^\"]+|~[/\\][^\"]+|[/\\][^\"]+)", goal)
        path = path_match.group(1) if path_match else str(Path.home() / "Downloads")
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
        lower_cmd = command.lower()
        if any(token in lower_cmd for token in ("remove-item", "rm ", "del ", "format-", "rmdir")):
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

    @staticmethod
    def _looks_like_workday_start(lower: str) -> bool:
        return any(
            phrase in lower
            for phrase in ("start my workday", "start workday", "begin my day", "open my work setup")
        )

    @staticmethod
    def _looks_like_workday_shutdown(lower: str) -> bool:
        return any(
            phrase in lower
            for phrase in ("end my workday", "shutdown workday", "finish my day", "wrap up work")
        )

    @staticmethod
    def _looks_like_diagnostic(lower: str) -> bool:
        return any(
            phrase in lower
            for phrase in ("diagnos", "troubleshoot", "disk space", "why won't", "why wont", "pc issue")
        )

    @staticmethod
    def _looks_like_dev_setup(lower: str) -> bool:
        return any(
            phrase in lower
            for phrase in ("set up a project", "setup project", "dev setup", "toolchain", "clone this repo")
        )

    @staticmethod
    def _looks_like_organise_downloads(lower: str) -> bool:
        return "download" in lower and any(w in lower for w in ("organis", "organiz", "sort", "file"))

    @staticmethod
    def _looks_like_list_files(lower: str) -> bool:
        return any(phrase in lower for phrase in ("list files", "show files", "what's in", "whats in"))

    @staticmethod
    def _looks_like_terminal(lower: str) -> bool:
        return lower.startswith("run ") or lower.startswith("execute ")
