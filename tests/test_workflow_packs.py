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
