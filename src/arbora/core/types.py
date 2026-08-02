"""Shared types for plans, tools, permissions, and audit events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "") -> str:
    stem = uuid4().hex[:12]
    return f"{prefix}{stem}" if prefix else stem


class Sensitivity(str, Enum):
    """How careful Arbora must be before a tool step runs."""

    READ = "read"
    MUTATE = "mutate"
    DESTRUCTIVE = "destructive"
    CREDENTIAL = "credential"
    FINANCIAL = "financial"


class AuthorityLevel(str, Enum):
    READ = "read"
    PROPOSE = "propose"
    EXECUTE_WITH_APPROVAL = "execute_with_approval"
    TRUSTED_ROUTINE = "trusted_routine"
    HARD_CONFIRMATION = "hard_confirmation"


HARD_CONFIRMATION_CLASSES = frozenset(
    {
        Sensitivity.DESTRUCTIVE,
        Sensitivity.CREDENTIAL,
        Sensitivity.FINANCIAL,
    }
)


@dataclass(frozen=True)
class ToolStep:
    """One inspectable action in a plan."""

    id: str
    adapter: str
    action: str
    args: dict[str, Any]
    summary: str
    sensitivity: Sensitivity
    side_effects: tuple[str, ...] = ()

    def requires_hard_confirmation(self) -> bool:
        return self.sensitivity in HARD_CONFIRMATION_CLASSES


@dataclass
class Plan:
    """A proposed sequence of tool steps for a user goal."""

    id: str
    goal: str
    steps: list[ToolStep]
    rationale: str = ""
    created_at: datetime = field(default_factory=utc_now)

    @property
    def has_hard_confirmation_steps(self) -> bool:
        return any(step.requires_hard_confirmation() for step in self.steps)


@dataclass(frozen=True)
class ScopeGrant:
    """Narrow permission for tools, paths, apps, or commands."""

    id: str
    adapter: str
    actions: frozenset[str]
    # Optional path/app/command constraints (empty = any within adapter+actions)
    paths: frozenset[str] = frozenset()
    apps: frozenset[str] = frozenset()
    commands: frozenset[str] = frozenset()


@dataclass
class TrustedRoutine:
    """Previously approved, scoped automation that may run without re-planning."""

    id: str
    name: str
    plan_fingerprint: str
    scopes: list[ScopeGrant]
    version: int = 1
    enabled: bool = True


@dataclass
class ApprovalDecision:
    plan_id: str
    approved_step_ids: frozenset[str]
    rejected_step_ids: frozenset[str]
    promote_to_trusted: bool = False
    trusted_name: str | None = None
    decided_at: datetime = field(default_factory=utc_now)


@dataclass
class StepResult:
    step_id: str
    ok: bool
    output: str
    error: str | None = None
    dry_run: bool = False


@dataclass
class ExecutionReport:
    plan_id: str
    results: list[StepResult]
    completed_at: datetime = field(default_factory=utc_now)

    @property
    def all_ok(self) -> bool:
        return all(result.ok for result in self.results)


@dataclass
class AuditEvent:
    id: str
    kind: str
    message: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
