"""Permission broker and planner regression tests."""

from __future__ import annotations

from pathlib import Path

from arbora.cli.session import approve_all, build_runtime, format_plan, hard_confirm_ids_for
from arbora.core.types import (
    ApprovalDecision,
    Sensitivity,
    ToolStep,
    new_id,
)
from arbora.core.types import Plan


def test_workday_plan_shape():
    runtime = build_runtime(memory_root=Path("."))
    plan = runtime.planner.plan("start my workday")
    assert plan.steps
    assert any(step.adapter == "desktop" for step in plan.steps)
    assert "workday" in plan.rationale.lower()


def test_diagnostic_is_read_only():
    runtime = build_runtime(memory_root=Path("."))
    plan = runtime.planner.plan("diagnose disk space on this PC")
    assert plan.steps
    assert all(step.sensitivity == Sensitivity.READ for step in plan.steps)


def test_broker_blocks_unapproved_mutate(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path)
    plan = runtime.planner.plan("start my workday")
    decision = ApprovalDecision(
        plan_id=plan.id,
        approved_step_ids=frozenset(),
        rejected_step_ids=frozenset(step.id for step in plan.steps),
    )
    results = runtime.broker.execute_plan(plan, decision, dry_run=True)
    assert results
    assert any(not r.ok for r in results)


def test_broker_allows_approved_dry_run(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path)
    plan = runtime.planner.plan("list files in ~/Downloads")
    decision = approve_all(plan)
    results = runtime.broker.execute_plan(plan, decision, dry_run=True)
    assert results
    assert all(r.ok for r in results)
    assert all(r.dry_run for r in results)


def test_hard_confirmation_required_for_destructive(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path)
    step = ToolStep(
        id=new_id("step_"),
        adapter="terminal",
        action="run_powershell",
        args={"command": "Remove-Item -Recurse C:\\temp\\demo"},
        summary="Delete demo folder",
        sensitivity=Sensitivity.DESTRUCTIVE,
        side_effects=("Permanent delete",),
    )
    plan = Plan(id=new_id("plan_"), goal="delete stuff", steps=[step], rationale="test")
    decision = approve_all(plan)
    results = runtime.broker.execute_plan(plan, decision, dry_run=True)
    assert len(results) == 1
    assert results[0].ok is False
    assert "Hard confirmation" in (results[0].error or "")

    results2 = runtime.broker.execute_plan(
        plan,
        decision,
        dry_run=True,
        hard_confirmed_step_ids=hard_confirm_ids_for(plan, True),
    )
    assert results2[0].ok is True


def test_promote_and_revoke_trusted_routine(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path)
    plan = runtime.planner.plan("list files in ~/Downloads")
    decision = approve_all(plan, promote_to_trusted=True, trusted_name="list-downloads")
    runtime.broker.execute_plan(plan, decision, dry_run=True)
    routines = runtime.broker.list_routines()
    assert len(routines) == 1
    assert routines[0].name == "list-downloads"
    assert runtime.broker.revoke_routine(routines[0].id) is True
    assert runtime.broker.list_routines() == []


def test_memory_roundtrip(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path)
    runtime.memory.set("theme", "focus")
    assert runtime.memory.get("theme") == "focus"
    runtime.memory.wipe()
    assert runtime.memory.get("theme") is None


def test_format_plan_includes_steps():
    runtime = build_runtime(memory_root=Path("."))
    plan = runtime.planner.plan("set up a project")
    text = format_plan(plan)
    assert "Plan " in text
    assert "Steps:" in text
