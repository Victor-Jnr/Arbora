"""Regression tests for opt-in user preferences."""

from __future__ import annotations

from pathlib import Path

from arbora.cli.session import approve_all, build_runtime
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


def test_downloads_folder_preference(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    custom = tmp_path / "Inbox"
    set_preference(runtime.memory, "downloads_folder", str(custom))
    runtime2 = build_runtime(memory_root=tmp_path, provider="echo")
    assert runtime2.preferences.resolved_downloads_folder() == custom
    plan = runtime2.planner.plan("organise my downloads")
    listed = next(step for step in plan.steps if step.action == "list_directory")
    assert str(custom) in listed.args["path"]
    listed_default = runtime2.planner.plan("list files")
    assert str(custom) in listed_default.steps[0].args["path"]


def test_screenshots_folder_preference_and_screenshot_plan(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    custom = tmp_path / "MyShots"
    set_preference(runtime.memory, "screenshots_folder", str(custom))
    runtime2 = build_runtime(memory_root=tmp_path, provider="echo")
    assert runtime2.preferences.resolved_screenshots_folder() == custom
    plan = runtime2.planner.plan("take a screenshot")
    ensure = next(step for step in plan.steps if step.action == "ensure_directory")
    capture = next(step for step in plan.steps if step.action == "capture_screenshot")
    assert str(custom) in ensure.args["path"]
    assert str(custom) in capture.args["path"]
    notes = runtime2.planner.plan("save a note about milk")
    write = next(step for step in notes.steps if step.action == "write_text")
    assert str(custom) not in write.args["path"]


def test_screenshots_folder_defaults_under_notes(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    custom_notes = tmp_path / "MyNotes"
    set_preference(runtime.memory, "notes_folder", str(custom_notes))
    runtime2 = build_runtime(memory_root=tmp_path, provider="echo")
    assert runtime2.preferences.resolved_screenshots_folder() == custom_notes / "screenshots"
    plan = runtime2.planner.plan("take a screenshot")
    ensure = next(step for step in plan.steps if step.action == "ensure_directory")
    assert str(custom_notes / "screenshots") in ensure.args["path"]


def test_notes_folder_preference_and_save_note_plan(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    custom = tmp_path / "MyNotes"
    set_preference(runtime.memory, "notes_folder", str(custom))
    runtime2 = build_runtime(memory_root=tmp_path, provider="echo")
    assert runtime2.preferences.resolved_notes_folder() == custom
    plan = runtime2.planner.plan("save a note about buying milk")
    assert "save-note" in plan.rationale.lower()
    ensure = next(step for step in plan.steps if step.action == "ensure_directory")
    write = next(step for step in plan.steps if step.action == "write_text")
    assert str(custom) in ensure.args["path"]
    assert str(custom) in write.args["path"]
    assert "buying milk" in write.args["content"]
    results = runtime2.broker.execute_plan(plan, approve_all(plan), dry_run=False)
    assert all(result.ok for result in results)
    written = list(custom.glob("note-*.txt"))
    assert len(written) == 1
    assert "buying milk" in written[0].read_text(encoding="utf-8")


def test_projects_folder_preference(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    custom = tmp_path / "Projects"
    set_preference(runtime.memory, "projects_folder", str(custom))
    runtime2 = build_runtime(memory_root=tmp_path, provider="echo")
    assert runtime2.preferences.resolved_projects_folder() == custom
    plan = runtime2.planner.plan("set up a project")
    ensure = next(step for step in plan.steps if step.action == "ensure_directory")
    assert str(custom) in ensure.args["path"]


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


def test_spoken_confirmations_preference(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    prefs = set_preference(runtime.memory, "spoken_confirmations", "on")
    assert prefs.spoken_confirmations is True
    runtime2 = build_runtime(memory_root=tmp_path, provider="echo")
    assert runtime2.preferences.spoken_confirmations is True
    assert runtime2.planner._spoken_confirmations is True  # noqa: SLF001


def test_prefs_cli_list(tmp_path: Path, capsys):
    from arbora.cli.prefs import run_prefs

    assert run_prefs(["--memory-dir", str(tmp_path), "list"]) == 0
    out = capsys.readouterr().out
    assert "dry_run_default" in out
    assert "run_schedules_on_start" in out
    assert "briefs_folder" in out
    assert "projects_folder" in out
    assert "downloads_folder" in out
    assert "notes_folder" in out
    assert "screenshots_folder" in out
    assert "spoken_confirmations" in out


def test_open_workday_folder_uses_workday_preference(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    custom = tmp_path / "MyWorkday"
    set_preference(runtime.memory, "workday_folder", str(custom))
    runtime2 = build_runtime(memory_root=tmp_path, provider="echo")
    plan = runtime2.planner.plan("open my workday folder")
    assert [step.action for step in plan.steps] == ["list_directory", "open_in_explorer"]
    assert str(custom) in plan.steps[0].args["path"]
    assert str(custom) in plan.steps[-1].args["path"]
    start = runtime2.planner.plan("start my workday")
    assert start.steps[0].action == "list_running_apps"
    assert not any(step.action == "open_in_explorer" for step in start.steps)
