"""Tests for reusable workflow packs."""

from __future__ import annotations

from pathlib import Path

from arbora.cli.session import approve_all, build_runtime
from arbora.workflows.packs import WorkflowPack, load_workflow_packs, match_workflow_pack


def test_load_bundled_workflow_packs():
    packs = load_workflow_packs()
    ids = {pack.id for pack in packs}
    assert "list-downloads" in ids
    assert "disk-diagnose" in ids
    assert "dev-project-setup" in ids
    assert "organise-downloads" in ids
    assert "git-status" in ids
    assert "largest-folders" in ids
    assert "pytest" in ids
    assert "find-files" in ids
    assert "inspect-temp" in ids
    assert "list-recent-downloads" in ids
    assert "list-recent-documents" in ids
    assert "inspect-clipboard" in ids
    assert "speak-confirmation" in ids
    assert "copy-file" in ids
    assert "take-screenshot" in ids
    assert "inspect-network" in ids
    assert "save-clipboard-note" in ids
    assert "inspect-old-downloads" in ids
    assert "inspect-battery" in ids
    assert "inspect-printers" in ids
    assert "inspect-startup" in ids
    assert "inspect-default-browser" in ids
    assert "inspect-display" in ids
    assert "inspect-windows-update" in ids
    assert "inspect-timezone" in ids


def test_match_workflow_pack_prefers_longest_phrase():
    packs = [
        WorkflowPack(
            id="a",
            name="A",
            description="",
            goal_phrases=("disk",),
            rationale="a",
            steps=(
                {
                    "adapter": "files",
                    "action": "list_directory",
                    "args": {"path": "."},
                    "summary": "list",
                    "sensitivity": "read",
                },
            ),
        ),
        WorkflowPack(
            id="b",
            name="B",
            description="",
            goal_phrases=("disk diagnose pack",),
            rationale="b",
            steps=(
                {
                    "adapter": "terminal",
                    "action": "run_powershell",
                    "args": {"command": "Get-Date"},
                    "summary": "date",
                    "sensitivity": "read",
                },
            ),
        ),
    ]
    matched = match_workflow_pack("run disk diagnose pack now", packs=packs)
    assert matched is not None
    assert matched.id == "b"


def test_workflow_pack_plan_via_runtime(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    plan = runtime.planner.plan("list downloads")
    assert "[workflow:list-downloads]" in plan.rationale
    assert plan.steps[0].adapter == "files"
    results = runtime.broker.execute_plan(plan, approve_all(plan), dry_run=True)
    assert results and results[0].ok


def test_largest_folders_workflow_pack_matches():
    pack = match_workflow_pack("run largest folders pack")
    assert pack is not None
    assert pack.id == "largest-folders"
    plan = pack.to_plan("run largest folders pack")
    assert plan is not None
    assert all(step.sensitivity.value == "read" for step in plan.steps)
    assert any(int(step.args.get("timeout_seconds", 0)) >= 300 for step in plan.steps)


def test_pytest_workflow_pack_matches():
    pack = match_workflow_pack("run pytest pack")
    assert pack is not None
    assert pack.id == "pytest"
    plan = pack.to_plan("run pytest pack")
    assert plan is not None
    assert plan.steps[0].sensitivity.value == "read"
    assert plan.steps[1].sensitivity.value == "mutate"
    assert all("pytest" in str(step.args.get("command", "")).lower() for step in plan.steps)


def test_find_files_workflow_pack_matches():
    pack = match_workflow_pack("run find files pack")
    assert pack is not None
    assert pack.id == "find-files"
    plan = pack.to_plan("run find files pack")
    assert plan is not None
    assert plan.steps[0].action == "search_by_name"
    assert plan.steps[0].sensitivity.value == "read"


def test_inspect_temp_workflow_pack_matches():
    pack = match_workflow_pack("run inspect temp pack")
    assert pack is not None
    assert pack.id == "inspect-temp"
    plan = pack.to_plan("run inspect temp pack")
    assert plan is not None
    assert plan.steps[0].action == "inspect_user_temp"
    assert plan.steps[0].sensitivity.value == "read"


def test_list_recent_downloads_workflow_pack_matches():
    pack = match_workflow_pack("run recent files pack")
    assert pack is not None
    assert pack.id == "list-recent-downloads"
    plan = pack.to_plan("run recent files pack")
    assert plan is not None
    assert plan.steps[0].action == "list_recent"


def test_list_recent_documents_workflow_pack_matches():
    pack = match_workflow_pack("run recent documents pack")
    assert pack is not None
    assert pack.id == "list-recent-documents"
    plan = pack.to_plan("run recent documents pack")
    assert plan is not None
    assert plan.steps[0].action == "list_recent"
    assert plan.steps[0].adapter == "files"
    assert plan.steps[0].sensitivity.value == "read"
    path = str(plan.steps[0].args.get("path", "")).lower()
    assert "documents" in path
    assert "downloads" not in path
    assert plan.steps[0].sensitivity.value == "read"


def test_inspect_clipboard_workflow_pack_matches():
    pack = match_workflow_pack("run inspect clipboard pack")
    assert pack is not None
    assert pack.id == "inspect-clipboard"
    plan = pack.to_plan("run inspect clipboard pack")
    assert plan is not None
    assert plan.steps[0].action == "inspect_clipboard"
    assert plan.steps[0].args.get("reveal") is False
    assert plan.steps[0].sensitivity.value == "read"


def test_speak_confirmation_workflow_pack_matches():
    pack = match_workflow_pack("run speak confirmation pack")
    assert pack is not None
    assert pack.id == "speak-confirmation"
    plan = pack.to_plan("run speak confirmation pack")
    assert plan is not None
    assert plan.steps[0].action == "speak_text"
    assert plan.steps[0].sensitivity.value == "mutate"


def test_copy_file_workflow_pack_matches():
    pack = match_workflow_pack("run copy file pack")
    assert pack is not None
    assert pack.id == "copy-file"
    plan = pack.to_plan("run copy file pack")
    assert plan is not None
    assert [step.action for step in plan.steps] == ["preview_copy_move", "copy_file"]
    assert plan.steps[0].sensitivity.value == "read"
    assert plan.steps[1].sensitivity.value == "mutate"


def test_take_screenshot_workflow_pack_matches():
    pack = match_workflow_pack("run screenshot pack")
    assert pack is not None
    assert pack.id == "take-screenshot"
    plan = pack.to_plan("run screenshot pack")
    assert plan is not None
    assert [step.action for step in plan.steps] == ["ensure_directory", "capture_screenshot"]
    assert plan.steps[-1].adapter == "desktop"
    assert plan.steps[-1].sensitivity.value == "mutate"


def test_inspect_network_workflow_pack_matches():
    pack = match_workflow_pack("run inspect network pack")
    assert pack is not None
    assert pack.id == "inspect-network"
    plan = pack.to_plan("run inspect network pack")
    assert plan is not None
    assert [step.action for step in plan.steps] == ["inspect_network"]
    assert plan.steps[0].sensitivity.value == "read"


def test_save_clipboard_note_workflow_pack_matches():
    pack = match_workflow_pack("run save clipboard note pack")
    assert pack is not None
    assert pack.id == "save-clipboard-note"
    plan = pack.to_plan("run save clipboard note pack")
    assert plan is not None
    assert [step.action for step in plan.steps] == ["ensure_directory", "save_clipboard_text"]
    assert plan.steps[-1].adapter == "desktop"
    assert plan.steps[-1].sensitivity.value == "mutate"


def test_inspect_old_downloads_workflow_pack_matches():
    pack = match_workflow_pack("run inspect old downloads pack")
    assert pack is not None
    assert pack.id == "inspect-old-downloads"
    plan = pack.to_plan("run inspect old downloads pack")
    assert plan is not None
    assert [step.action for step in plan.steps] == ["inspect_old_files"]
    assert plan.steps[0].args["older_than_days"] == 30
    assert plan.steps[0].sensitivity.value == "read"


def test_inspect_battery_workflow_pack_matches():
    pack = match_workflow_pack("run inspect battery pack")
    assert pack is not None
    assert pack.id == "inspect-battery"
    plan = pack.to_plan("run inspect battery pack")
    assert plan is not None
    assert [step.action for step in plan.steps] == ["inspect_battery"]
    assert plan.steps[0].sensitivity.value == "read"


def test_close_window_workflow_pack_matches():
    pack = match_workflow_pack("run close window pack")
    assert pack is not None
    assert pack.id == "close-window"
    plan = pack.to_plan("run close window pack")
    assert plan is not None
    assert [step.action for step in plan.steps] == ["close_window"]
    assert plan.steps[0].adapter == "desktop"
    assert plan.steps[0].sensitivity.value == "mutate"
    assert plan.steps[0].args.get("title_contains")


def test_open_url_installed_browser_workflow_pack_matches():
    pack = match_workflow_pack("run open url in chrome pack")
    assert pack is not None
    assert pack.id == "open-url-installed-browser"
    plan = pack.to_plan("run open url in chrome pack")
    assert plan is not None
    assert [step.action for step in plan.steps] == ["open_in_browser"]
    assert plan.steps[0].adapter == "desktop"
    assert plan.steps[0].sensitivity.value == "mutate"
    assert str(plan.steps[0].args.get("url", "")).startswith("https://")
    assert plan.steps[0].args.get("name") in {"chrome", "edge", "firefox"}


def test_inspect_printers_workflow_pack_matches():
    pack = match_workflow_pack("run inspect printers pack")
    assert pack is not None
    assert pack.id == "inspect-printers"
    plan = pack.to_plan("run inspect printers pack")
    assert plan is not None
    assert [step.action for step in plan.steps] == ["inspect_printers"]
    assert plan.steps[0].adapter == "desktop"
    assert plan.steps[0].sensitivity.value == "read"


def test_inspect_startup_workflow_pack_matches():
    pack = match_workflow_pack("run inspect startup pack")
    assert pack is not None
    assert pack.id == "inspect-startup"
    plan = pack.to_plan("run inspect startup pack")
    assert plan is not None
    assert [step.action for step in plan.steps] == ["inspect_startup"]
    assert plan.steps[0].adapter == "desktop"
    assert plan.steps[0].sensitivity.value == "read"


def test_inspect_default_browser_workflow_pack_matches():
    pack = match_workflow_pack("run inspect default browser pack")
    assert pack is not None
    assert pack.id == "inspect-default-browser"
    plan = pack.to_plan("run inspect default browser pack")
    assert plan is not None
    assert [step.action for step in plan.steps] == ["inspect_default_browser"]
    assert plan.steps[0].adapter == "desktop"
    assert plan.steps[0].sensitivity.value == "read"


def test_inspect_display_workflow_pack_matches():
    pack = match_workflow_pack("run inspect display pack")
    assert pack is not None
    assert pack.id == "inspect-display"
    plan = pack.to_plan("run inspect display pack")
    assert plan is not None
    assert [step.action for step in plan.steps] == ["inspect_display"]
    assert plan.steps[0].adapter == "desktop"
    assert plan.steps[0].sensitivity.value == "read"


def test_inspect_windows_update_workflow_pack_matches():
    pack = match_workflow_pack("run inspect windows update pack")
    assert pack is not None
    assert pack.id == "inspect-windows-update"
    plan = pack.to_plan("run inspect windows update pack")
    assert plan is not None
    assert [step.action for step in plan.steps] == ["inspect_windows_update"]
    assert plan.steps[0].adapter == "desktop"
    assert plan.steps[0].sensitivity.value == "read"


def test_inspect_timezone_workflow_pack_matches():
    pack = match_workflow_pack("run inspect timezone pack")
    assert pack is not None
    assert pack.id == "inspect-timezone"
    plan = pack.to_plan("run inspect timezone pack")
    assert plan is not None
    assert [step.action for step in plan.steps] == ["inspect_timezone"]
    assert plan.steps[0].adapter == "desktop"
    assert plan.steps[0].sensitivity.value == "read"


def test_git_status_workflow_pack_matches():
    pack = match_workflow_pack("run git status pack")
    assert pack is not None
    assert pack.id == "git-status"
    plan = pack.to_plan("run git status pack")
    assert plan is not None
    assert all(step.adapter == "terminal" for step in plan.steps)
    assert all(step.sensitivity.value == "read" for step in plan.steps)


def test_organise_downloads_workflow_pack_matches():
    pack = match_workflow_pack("run organise downloads pack")
    assert pack is not None
    assert pack.id == "organise-downloads"
    plan = pack.to_plan("run organise downloads pack")
    assert plan is not None
    actions = [step.action for step in plan.steps]
    assert actions == ["list_directory", "preview_organise", "apply_organise"]


def test_dev_project_workflow_pack_matches():
    pack = match_workflow_pack("run dev project pack")
    assert pack is not None
    assert pack.id == "dev-project-setup"
    plan = pack.to_plan("run dev project pack")
    assert plan is not None
    assert any(step.action == "write_text" for step in plan.steps)


def test_dev_setup_journey_scaffolds_project_files(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runtime = build_runtime(memory_root=tmp_path / "memory", provider="echo")
    plan = runtime.planner.plan("set up a project")
    assert any(step.action == "write_text" for step in plan.steps)
    results = runtime.broker.execute_plan(plan, approve_all(plan), dry_run=False)
    assert all(result.ok for result in results)
    assert (tmp_path / "README.md").exists()
    assert (tmp_path / ".gitignore").exists()


def test_user_workflow_pack_override(tmp_path: Path, monkeypatch):
    user_dir = tmp_path / "workflows"
    user_dir.mkdir()
    (user_dir / "list-downloads.json").write_text(
        """
        {
          "id": "list-downloads",
          "name": "Custom downloads",
          "description": "custom",
          "goal_phrases": ["list downloads"],
          "rationale": "custom pack",
          "steps": [
            {
              "adapter": "files",
              "action": "list_directory",
              "args": {"path": "~/Desktop"},
              "summary": "List Desktop instead",
              "sensitivity": "read"
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr("arbora.workflows.packs._user_workflows_dir", lambda: user_dir)
    pack = match_workflow_pack("list downloads", packs=load_workflow_packs())
    assert pack is not None
    plan = pack.to_plan("list downloads")
    assert plan is not None
    assert plan.steps[0].args["path"] == "~/Desktop"
