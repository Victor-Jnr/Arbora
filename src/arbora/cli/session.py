"""Session orchestration: plan → approve → execute through the broker."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from arbora.adapters import BrowserAdapter, DesktopAdapter, FilesAdapter, TerminalAdapter
from arbora.core.audit import AuditLog
from arbora.core.broker import PermissionBroker
from arbora.core.planner import GoalPlanner
from arbora.core.routines_store import routines_from_dicts, routines_to_dicts
from arbora.core.types import (
    ApprovalDecision,
    ExecutionReport,
    Plan,
    Sensitivity,
    TrustedRoutine,
    new_id,
)
from arbora.memory import LocalMemoryStore
from arbora.providers import EchoProvider, OllamaProvider
from arbora.providers.base import ModelProvider


@dataclass
class Runtime:
    audit: AuditLog
    broker: PermissionBroker
    planner: GoalPlanner
    memory: LocalMemoryStore
    provider_name: str


def select_provider(name: str | None = None) -> ModelProvider:
    choice = (name or os.environ.get("ARBORA_PROVIDER") or "ollama").strip().lower()
    if choice in {"echo", "echo-local", "none", "off"}:
        return EchoProvider()
    if choice == "ollama":
        return OllamaProvider()
    raise ValueError(f"Unknown provider '{choice}'. Use ollama or echo.")


def build_runtime(memory_root: Path | None = None, provider: str | None = None) -> Runtime:
    audit = AuditLog()
    broker = PermissionBroker(audit)
    broker.register_adapter(DesktopAdapter())
    broker.register_adapter(FilesAdapter())
    broker.register_adapter(TerminalAdapter())
    broker.register_adapter(BrowserAdapter())
    memory = LocalMemoryStore(root=memory_root)
    broker.load_routines(routines_from_dicts(memory.get("trusted_routines")))
    model = select_provider(provider)
    planner = GoalPlanner(provider=model)
    return Runtime(
        audit=audit,
        broker=broker,
        planner=planner,
        memory=memory,
        provider_name=getattr(model, "name", "unknown"),
    )


def persist_routines(runtime: Runtime) -> None:
    runtime.memory.set("trusted_routines", routines_to_dicts(runtime.broker.list_routines()))


def format_plan(plan: Plan) -> str:
    lines = [
        f"Plan {plan.id}",
        f"Goal: {plan.goal}",
        f"Rationale: {plan.rationale}",
        "Steps:",
    ]
    for index, step in enumerate(plan.steps, start=1):
        risk = step.sensitivity.value
        hard = " [HARD CONFIRM]" if step.requires_hard_confirmation() else ""
        lines.append(f"  {index}. [{risk}]{hard} {step.summary}")
        lines.append(f"     adapter={step.adapter} action={step.action}")
        if step.side_effects:
            lines.append(f"     side effects: {'; '.join(step.side_effects)}")
    return "\n".join(lines)


def approve_all(plan: Plan, *, promote_to_trusted: bool = False, trusted_name: str | None = None) -> ApprovalDecision:
    return ApprovalDecision(
        plan_id=plan.id,
        approved_step_ids=frozenset(step.id for step in plan.steps),
        rejected_step_ids=frozenset(),
        promote_to_trusted=promote_to_trusted,
        trusted_name=trusted_name,
    )


def hard_confirm_ids_for(plan: Plan, confirmed: bool) -> frozenset[str]:
    if not confirmed:
        return frozenset()
    return frozenset(step.id for step in plan.steps if step.requires_hard_confirmation())


def run_goal(
    runtime: Runtime,
    goal: str,
    *,
    dry_run: bool = False,
    auto_approve: bool = False,
    hard_confirm: bool = False,
    promote_name: str | None = None,
) -> tuple[Plan, ExecutionReport, TrustedRoutine | None]:
    plan = runtime.planner.plan(goal)
    runtime.audit.record("plan_created", plan.rationale or plan.goal, plan_id=plan.id, goal=goal)
    matched = runtime.broker.find_matching_routine(plan)

    if matched is not None:
        hard_ids = hard_confirm_ids_for(plan, hard_confirm)
        if plan.has_hard_confirmation_steps and not hard_confirm:
            hard_step_ids = {step.id for step in plan.steps if step.requires_hard_confirmation()}
            decision = ApprovalDecision(
                plan_id=plan.id,
                approved_step_ids=frozenset(step.id for step in plan.steps if step.id not in hard_step_ids),
                rejected_step_ids=frozenset(hard_step_ids),
            )
        else:
            decision = approve_all(plan)
        results = runtime.broker.execute_plan(
            plan,
            decision,
            dry_run=dry_run,
            hard_confirmed_step_ids=hard_ids,
        )
        report = ExecutionReport(plan_id=plan.id, results=results)
        runtime.memory.set("last_goal", goal)
        runtime.memory.set("last_plan_id", plan.id)
        return plan, report, matched

    if not auto_approve:
        raise ValueError("run_goal requires auto_approve=True for non-interactive use")

    decision = approve_all(
        plan,
        promote_to_trusted=promote_name is not None,
        trusted_name=promote_name,
    )
    hard_ids = hard_confirm_ids_for(plan, hard_confirm)
    if plan.has_hard_confirmation_steps and not hard_confirm:
        hard_step_ids = {step.id for step in plan.steps if step.requires_hard_confirmation()}
        decision = ApprovalDecision(
            plan_id=plan.id,
            approved_step_ids=frozenset(step.id for step in plan.steps if step.id not in hard_step_ids),
            rejected_step_ids=frozenset(hard_step_ids),
            promote_to_trusted=False,
        )

    results = runtime.broker.execute_plan(
        plan,
        decision,
        dry_run=dry_run,
        hard_confirmed_step_ids=hard_ids,
    )
    report = ExecutionReport(plan_id=plan.id, results=results)
    runtime.audit.record(
        "plan_finished",
        f"Plan {plan.id} finished ok={report.all_ok}",
        plan_id=plan.id,
    )
    if promote_name:
        persist_routines(runtime)
    runtime.memory.set("last_goal", goal)
    runtime.memory.set("last_plan_id", plan.id)
    return plan, report, None


def sensitivity_badge(sensitivity: Sensitivity) -> str:
    return {
        Sensitivity.READ: "read",
        Sensitivity.MUTATE: "mutate",
        Sensitivity.DESTRUCTIVE: "DESTRUCTIVE",
        Sensitivity.CREDENTIAL: "CREDENTIAL",
        Sensitivity.FINANCIAL: "FINANCIAL",
    }[sensitivity]


__all__ = [
    "Runtime",
    "approve_all",
    "build_runtime",
    "format_plan",
    "hard_confirm_ids_for",
    "persist_routines",
    "run_goal",
    "select_provider",
    "sensitivity_badge",
    "new_id",
]
