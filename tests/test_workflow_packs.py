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
    assert "inspect-clipboard" in ids
    assert "speak-confirmation" in ids
    assert "copy-file" in ids
    assert "take-screenshot" in ids
    assert "inspect-network" in ids


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
