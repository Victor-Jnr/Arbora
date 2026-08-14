"""Regression tests for trusted-routine schedules."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from arbora.cli.session import approve_all, build_runtime, persist_routines
from arbora.schedules.runner import is_due, run_due_schedules, run_schedule
from arbora.schedules.store import add_schedule, load_schedules, parse_days, parse_time, remove_schedule


def _runtime(tmp_path: Path):
    return build_runtime(memory_root=tmp_path, provider="echo")


def _promote_downloads(runtime) -> str:
    plan = runtime.planner.plan("list files in ~/Downloads")
    runtime.broker.execute_plan(
        plan,
        approve_all(plan, promote_to_trusted=True, trusted_name="list-downloads"),
        dry_run=True,
    )
    persist_routines(runtime)
    routines = runtime.broker.list_routines()
    assert len(routines) == 1
    return routines[0].id


def test_parse_time_and_days():
    assert parse_time("09:30") == (9, 30)
    assert parse_days("mon,wed,fri") == frozenset({0, 2, 4})
    assert parse_days(None) == frozenset()


def test_add_and_remove_schedule(tmp_path: Path):
    runtime = _runtime(tmp_path)
    routine_id = _promote_downloads(runtime)
    schedule = add_schedule(runtime.memory, routine_id=routine_id, time_hhmm="08:00", days="mon")
    schedules = load_schedules(runtime.memory)
    assert len(schedules) == 1
    assert schedules[0].id == schedule.id
    assert schedules[0].dry_run is True
    assert remove_schedule(runtime.memory, schedule.id) is True
    assert load_schedules(runtime.memory) == []


def test_is_due_respects_last_run_date(tmp_path: Path):
    runtime = _runtime(tmp_path)
    routine_id = _promote_downloads(runtime)
    schedule = add_schedule(runtime.memory, routine_id=routine_id, time_hhmm="08:00")
    schedule = load_schedules(runtime.memory)[0]

    morning = datetime(2026, 8, 12, 9, 0, tzinfo=timezone.utc)
    assert is_due(schedule, morning) is True

    schedule.last_run_date = "2026-08-12"
    assert is_due(schedule, morning) is False


def test_run_schedule_matches_trusted_routine(tmp_path: Path):
    runtime = _runtime(tmp_path)
    routine_id = _promote_downloads(runtime)
    schedule = add_schedule(runtime.memory, routine_id=routine_id, time_hhmm="08:00")
    schedule = load_schedules(runtime.memory)[0]

    result = run_schedule(runtime, schedule, dry_run=True)
    assert result.skipped is False
    assert result.ok is True
    assert result.report is not None
    assert result.report.all_ok is True
    assert load_schedules(runtime.memory)[0].last_run_date is not None


def test_run_due_only_fires_once_per_day(tmp_path: Path):
    runtime = _runtime(tmp_path)
    routine_id = _promote_downloads(runtime)
    add_schedule(runtime.memory, routine_id=routine_id, time_hhmm="08:00")

    now = datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)
    first = run_due_schedules(runtime, now=now)
    assert len(first) == 1
    assert first[0].ok is True

    second = run_due_schedules(runtime, now=now)
    assert second == []


def test_schedule_skips_missing_routine(tmp_path: Path):
    runtime = _runtime(tmp_path)
    schedule = add_schedule(runtime.memory, routine_id="missing", time_hhmm="08:00")
    schedule = load_schedules(runtime.memory)[0]
    result = run_schedule(runtime, schedule)
    assert result.skipped is True
    assert result.ok is False


def test_schedule_cli_list_and_add(tmp_path: Path, capsys):
    from arbora.cli.schedule import run_schedule_cli

    runtime = _runtime(tmp_path)
    routine_id = _promote_downloads(runtime)

    assert run_schedule_cli(["--memory-dir", str(tmp_path), "--provider", "echo", "list"]) == 0
    assert "(no schedules)" in capsys.readouterr().out

    code = run_schedule_cli(
        [
            "--memory-dir",
            str(tmp_path),
            "--provider",
            "echo",
            "add",
            routine_id,
            "07:15",
            "--days",
            "mon,fri",
        ]
    )
    assert code == 0
    assert "Added schedule" in capsys.readouterr().out

    assert run_schedule_cli(["--memory-dir", str(tmp_path), "--provider", "echo", "list"]) == 0
    out = capsys.readouterr().out
    assert "07:15" in out
    assert "mon,fri" in out
