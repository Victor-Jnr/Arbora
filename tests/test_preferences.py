"""Regression tests for opt-in user preferences."""

from __future__ import annotations

from pathlib import Path

from arbora.cli.session import build_runtime
from arbora.preferences.store import set_preference


def test_set_and_load_preferences(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    prefs = set_preference(runtime.memory, "dry_run", "off")
    assert prefs.dry_run_default is False

    prefs = set_preference(runtime.memory, "workday_folder", str(tmp_path / "MyWorkday"))
    assert prefs.resolved_workday_folder() == tmp_path / "MyWorkday"

    runtime2 = build_runtime(memory_root=tmp_path, provider="echo")
    assert runtime2.preferences.dry_run_default is False
    assert runtime2.planner._workday_root == tmp_path / "MyWorkday"  # noqa: SLF001


def test_preferences_provider_override(tmp_path: Path):
    set_preference(build_runtime(memory_root=tmp_path, provider="echo").memory, "provider", "echo")
    runtime = build_runtime(memory_root=tmp_path)
    assert runtime.provider_name in {"echo", "echo-local"}


def test_briefs_folder_preference(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    custom = tmp_path / "MyBriefs"
    set_preference(runtime.memory, "briefs_folder", str(custom))
    runtime2 = build_runtime(memory_root=tmp_path, provider="echo")
    assert runtime2.preferences.resolved_briefs_folder() == custom
    plan = runtime2.planner.plan("research https://example.com")
    ensure = next(step for step in plan.steps if step.action == "ensure_directory")
    assert str(custom) in ensure.args["path"]


def test_run_schedules_on_start_preference(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    prefs = set_preference(runtime.memory, "run_schedules_on_start", "on")
    assert prefs.run_due_schedules_on_start is True
    runtime2 = build_runtime(memory_root=tmp_path, provider="echo")
    assert runtime2.preferences.run_due_schedules_on_start is True


def test_prefs_cli_list(tmp_path: Path, capsys):
    from arbora.cli.prefs import run_prefs

    assert run_prefs(["--memory-dir", str(tmp_path), "list"]) == 0
    out = capsys.readouterr().out
    assert "dry_run_default" in out
    assert "run_schedules_on_start" in out
    assert "briefs_folder" in out
