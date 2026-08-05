"""Goal planner — turns natural-language goals into inspectable tool plans.

Known journeys use deterministic templates. Unmatched goals may use a model
provider (e.g. local Ollama) to propose a JSON plan, which is validated before
returning. Models propose; the permission broker still disposes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from arbora.core.types import Plan, Sensitivity, ToolStep, new_id
from arbora.providers.base import ModelProvider

ALLOWED_ACTIONS: dict[str, frozenset[str]] = {
    "desktop": frozenset({"list_running_apps", "launch_app", "focus_window"}),
    "files": frozenset({"list_directory", "ensure_directory", "write_text", "preview_organise"}),
    "terminal": frozenset({"run_powershell"}),
}

SENSITIVITY_VALUES = {item.value: item for item in Sensitivity}


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
            args = item.get("args") if isinstance(item.get("args"), dict) else {}
            sens_raw = str(item.get("sensitivity", "read")).strip().lower()
            sensitivity = SENSITIVITY_VALUES.get(sens_raw, Sensitivity.READ)
            # Force destructive detection for dangerous shell commands.
            if adapter == "terminal" and action == "run_powershell":
                command = str(args.get("command", "")).lower()
                if any(token in command for token in ("remove-item", "rm ", "del ", "format-", "rmdir")):
                    sensitivity = Sensitivity.DESTRUCTIVE
            side = item.get("side_effects") if isinstance(item.get("side_effects"), list) else []
            steps.append(
                ToolStep(
                    id=new_id("step_"),
                    adapter=adapter,
                    action=action,
                    args=dict(args),
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
                    adapter="desktop",
                    action="focus_window",
                    args={"title_contains": "Notepad"},
                    summary="Focus the Notepad window if it is open",
                    sensitivity=Sensitivity.MUTATE,
                    side_effects=("Brings an existing window to the foreground",),
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
        return "download" in lower and any(
            w in lower for w in ("organis", "organiz", "sort my", "sort the", "filing")
        )
    @staticmethod
    def _looks_like_list_files(lower: str) -> bool:
        return any(phrase in lower for phrase in ("list files", "show files", "what's in", "whats in"))

    @staticmethod
    def _looks_like_terminal(lower: str) -> bool:
        return lower.startswith("run ") or lower.startswith("execute ")
