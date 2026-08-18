"""Regression tests for recent goal history."""

from __future__ import annotations

from pathlib import Path

from arbora.cli.session import build_runtime
from arbora.memory.goal_history import list_recent_goals, load_goals, record_goal


def test_record_and_list_goals(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    record_goal(runtime.memory, "start my workday")
    record_goal(runtime.memory, "diagnose disk space")
    record_goal(runtime.memory, "start my workday")

    recent = list_recent_goals(runtime.memory)
    assert recent == ["start my workday", "diagnose disk space"]

    runtime2 = build_runtime(memory_root=tmp_path, provider="echo")
    assert load_goals(runtime2.memory) == ["diagnose disk space", "start my workday"]


def test_record_skips_commands_and_blank(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    record_goal(runtime.memory, "/help")
    record_goal(runtime.memory, "   ")
    assert load_goals(runtime.memory) == []
