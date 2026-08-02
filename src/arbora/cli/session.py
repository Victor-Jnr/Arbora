"""Session orchestration: plan → approve → execute through the broker."""

from __future__ import annotations

from dataclasses import dataclass

from arbora.adapters import DesktopAdapter, FilesAdapter, TerminalAdapter
from arbora.core.audit import AuditLog
from arbora.core.broker import PermissionBroker
from arbora.core.planner import GoalPlanner
from arbora.core.types import (
    ApprovalDecision,
    ExecutionReport,
    Plan,
    Sensitivity,
    new_id,
)
from arbora.memory import LocalMemoryStore
from arbora.providers import EchoProvider


@dataclass
class Runtime:
    audit: AuditLog
    broker: PermissionBroker
    planner: GoalPlanner
    memory: LocalMemoryStore


def build_runtime(memory_root=None) -> Runtime:
    audit = AuditLog()
    broker = PermissionBroker(audit)
    broker.register_adapter(DesktopAdapter())
    broker.register_adapter(FilesAdapter())
    broker.register_adapter(TerminalAdapter())
    planner = GoalPlanner(provider=EchoProvider())
    memory = LocalMemoryStore(root=memory_root)
    return Runtime(audit=audit, broker=broker, planner=planner, memory=memory)


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
) -> tuple[Plan, ExecutionReport]:
    plan = runtime.planner.plan(goal)
    runtime.audit.record("plan_created", plan.rationale or plan.goal, plan_id=plan.id, goal=goal)

    if not auto_approve:
        raise ValueError("run_goal requires auto_approve=True for non-interactive use")

    decision = approve_all(
        plan,
        promote_to_trusted=promote_name is not None,
        trusted_name=promote_name,
    )
    hard_ids = hard_confirm_ids_for(plan, hard_confirm)
    # Auto path still refuses hard-confirmation classes unless explicitly confirmed.
    if plan.has_hard_confirmation_steps and not hard_confirm:
        # Reject hard steps; approve the rest.
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
    runtime.memory.set("last_goal", goal)
    runtime.memory.set("last_plan_id", plan.id)
    return plan, report


def sensitivity_badge(sensitivity: Sensitivity) -> str:
    return {
        Sensitivity.READ: "read",
        Sensitivity.MUTATE: "mutate",
        Sensitivity.DESTRUCTIVE: "DESTRUCTIVE",
        Sensitivity.CREDENTIAL: "CREDENTIAL",
        Sensitivity.FINANCIAL: "FINANCIAL",
    }[sensitivity]


# Keep new_id import used by tests/helpers if needed.
__all__ = [
    "Runtime",
    "approve_all",
    "build_runtime",
    "format_plan",
    "hard_confirm_ids_for",
    "run_goal",
    "sensitivity_badge",
    "new_id",
]
