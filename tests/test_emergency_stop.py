"""Emergency stop behaviour for the permission broker."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from arbora.cli.session import approve_all, build_runtime
from arbora.core.types import StepResult, new_id


class _StopOnFirstAdapter:
    name = "files"

    def __init__(self, broker) -> None:
        self.broker = broker
        self.calls = 0

    def execute(self, action: str, args: dict[str, Any], *, dry_run: bool = False) -> StepResult:
        self.calls += 1
        if self.calls == 1:
            self.broker.request_stop()
        return StepResult(
            step_id=new_id("res_"),
            ok=True,
            output=f"ran {action}",
            dry_run=dry_run,
        )


def test_emergency_stop_skips_remaining_steps(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    stopper = _StopOnFirstAdapter(runtime.broker)
    runtime.broker.register_adapter(stopper)

    plan = runtime.planner.plan("organise my downloads")
    assert len(plan.steps) >= 2
    results = runtime.broker.execute_plan(plan, approve_all(plan), dry_run=True)
    assert len(results) == len(plan.steps)
    assert results[0].ok is True
    assert all((r.error or "").startswith("Emergency stop") for r in results[1:])
    kinds = [e.kind for e in runtime.audit.events()]
    assert "emergency_stop_requested" in kinds
    assert "plan_stopped" in kinds
    assert runtime.broker.is_executing is False


def test_emergency_stop_blocks_promote(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    stopper = _StopOnFirstAdapter(runtime.broker)
    runtime.broker.register_adapter(stopper)
    plan = runtime.planner.plan("list files in ~/Downloads")
    # Force multi-step by using organise journey instead.
    plan = runtime.planner.plan("organise my downloads")
    decision = approve_all(plan, promote_to_trusted=True, trusted_name="should-not-promote")
    runtime.broker.execute_plan(plan, decision, dry_run=True)
    assert runtime.broker.list_routines() == []
