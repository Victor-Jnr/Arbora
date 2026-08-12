"""Reusable workflow packs — named, inspectable step templates."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arbora.core.tool_catalog import ALLOWED_ACTIONS
from arbora.core.types import Plan, Sensitivity, ToolStep, new_id

SENSITIVITY_VALUES = {item.value: item for item in Sensitivity}


@dataclass(frozen=True)
class WorkflowPack:
    id: str
    name: str
    description: str
    goal_phrases: tuple[str, ...]
    rationale: str
    steps: tuple[dict[str, Any], ...]

    def matches(self, goal: str) -> bool:
        lower = " ".join(goal.strip().lower().split())
        for phrase in self.goal_phrases:
            if phrase in lower:
                return True
        return False

    def to_plan(self, goal: str) -> Plan | None:
        steps: list[ToolStep] = []
        for item in self.steps:
            adapter = str(item.get("adapter", "")).strip()
            action = str(item.get("action", "")).strip()
            if adapter not in ALLOWED_ACTIONS or action not in ALLOWED_ACTIONS[adapter]:
                return None
            args = item.get("args") if isinstance(item.get("args"), dict) else {}
            sens_raw = str(item.get("sensitivity", "read")).strip().lower()
            sensitivity = SENSITIVITY_VALUES.get(sens_raw, Sensitivity.READ)
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
        if not steps:
            return None
        return Plan(
            id=new_id("plan_"),
            goal=goal,
            rationale=f"[workflow:{self.id}] {self.rationale}",
            steps=steps,
        )


def _repo_workflows_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "workflows"


def _user_workflows_dir() -> Path:
    return Path.home() / ".arbora" / "workflows"


def load_workflow_packs(extra_dirs: list[Path] | None = None) -> list[WorkflowPack]:
    dirs = [_repo_workflows_dir(), _user_workflows_dir()]
    if extra_dirs:
        dirs.extend(extra_dirs)
    by_id: dict[str, WorkflowPack] = {}
    for directory in dirs:
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.json")):
            pack = _load_pack_file(path)
            if pack is None:
                continue
            by_id[pack.id] = pack
    return list(by_id.values())


def _load_pack_file(path: Path) -> WorkflowPack | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    pack_id = str(data.get("id", "")).strip()
    if not pack_id:
        return None
    phrases = data.get("goal_phrases") or []
    if not isinstance(phrases, list):
        phrases = []
    steps = data.get("steps") or []
    if not isinstance(steps, list) or not steps:
        return None
    return WorkflowPack(
        id=pack_id,
        name=str(data.get("name") or pack_id),
        description=str(data.get("description") or ""),
        goal_phrases=tuple(str(p).strip().lower() for p in phrases if str(p).strip()),
        rationale=str(data.get("rationale") or data.get("description") or f"Workflow pack {pack_id}"),
        steps=tuple(item for item in steps if isinstance(item, dict)),
    )


def match_workflow_pack(goal: str, packs: list[WorkflowPack] | None = None) -> WorkflowPack | None:
    rows = packs if packs is not None else load_workflow_packs()
    lower = " ".join(goal.strip().lower().split())
    best: WorkflowPack | None = None
    best_len = -1
    for pack in rows:
        for phrase in pack.goal_phrases:
            if phrase in lower and len(phrase) > best_len:
                best = pack
                best_len = len(phrase)
    return best


def workflow_pack_rows(packs: list[WorkflowPack] | None = None) -> list[str]:
    rows: list[str] = []
    for pack in packs if packs is not None else load_workflow_packs():
        phrases = ", ".join(pack.goal_phrases[:3])
        rows.append(f"{pack.id}: {pack.name} — {pack.description} (phrases: {phrases})")
    return rows
