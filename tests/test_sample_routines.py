"""Tests for read-only sample trusted routines."""

from __future__ import annotations

from pathlib import Path

from arbora.cli.session import build_runtime
from arbora.core.sample_routines import SAMPLE_SPECS, seed_sample_routines
from arbora.core.types import Sensitivity


def test_seed_installs_read_only_samples(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    added = seed_sample_routines(runtime.broker, runtime.planner, runtime.memory)
    assert added == len(SAMPLE_SPECS)
    names = {routine.name for routine in runtime.broker.list_routines()}
    assert names == {"list-downloads", "disk-diagnose"}
    for routine in runtime.broker.list_routines():
        plan = runtime.planner.plan(routine.goal_text)
        assert runtime.broker.find_matching_routine(plan) is not None
        assert all(step.sensitivity == Sensitivity.READ for step in plan.steps)


def test_seed_is_idempotent(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo", seed_samples=True)
    assert len(runtime.broker.list_routines()) == 2
    runtime2 = build_runtime(memory_root=tmp_path, provider="echo", seed_samples=True)
    assert len(runtime2.broker.list_routines()) == 2
    added = seed_sample_routines(runtime2.broker, runtime2.planner, runtime2.memory)
    assert added == 0


def test_seed_does_not_run_without_flag(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    assert runtime.broker.list_routines() == []
