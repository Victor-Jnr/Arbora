"""Permission broker, planner, trusted routines, and provider regression tests."""

from __future__ import annotations

from pathlib import Path

from arbora.cli.session import approve_all, build_runtime, format_plan, hard_confirm_ids_for, persist_routines
from arbora.core.planner import GoalPlanner
from arbora.core.types import (
    ApprovalDecision,
    Plan,
    Sensitivity,
    ToolStep,
    new_id,
)


def _runtime(tmp_path: Path | None = None):
    root = tmp_path if tmp_path is not None else Path(".")
    return build_runtime(memory_root=root, provider="echo")


def test_save_note_alt_phrasing():
    runtime = _runtime()
    plan = runtime.planner.plan("jot down pick up the keys")
    assert "save-note" in plan.rationale.lower()
    assert any(step.action == "write_text" for step in plan.steps)
    write = next(step for step in plan.steps if step.action == "write_text")
    assert "pick up the keys" in write.args["content"]


def test_workday_plan_shape():
    runtime = _runtime()
    plan = runtime.planner.plan("start my workday")
    assert plan.steps
    assert any(step.adapter == "desktop" for step in plan.steps)
    assert any(step.action == "write_text" for step in plan.steps)
    assert "workday" in plan.rationale.lower()
    assert "read" in plan.rationale.lower()


def test_workday_alt_phrasing():
    runtime = _runtime()
    plan = runtime.planner.plan("morning setup please")
    assert "workday" in plan.rationale.lower()


def test_largest_folders_journey_is_read_only():
    runtime = _runtime()
    plan = runtime.planner.plan("what folderis using the most amout of storage in c drive")
    assert plan.steps
    assert all(step.sensitivity == Sensitivity.READ for step in plan.steps)
    assert "largest-folder" in plan.rationale.lower()
    assert any(int(step.args.get("timeout_seconds", 0)) >= 300 for step in plan.steps)
    command = " ".join(str(step.args.get("command", "")) for step in plan.steps)
    assert "C:\\" in command
    assert "GetFolder" in command


def test_largest_folders_uses_named_drive():
    runtime = _runtime()
    plan = runtime.planner.plan("largest folder on D drive")
    command = " ".join(str(step.args.get("command", "")) for step in plan.steps)
    assert "D:\\" in command
    assert all(step.sensitivity == Sensitivity.READ for step in plan.steps)


def test_diagnostic_still_matches_disk_space_goal():
    runtime = _runtime()
    plan = runtime.planner.plan("diagnose disk space on this PC")
    assert plan.steps
    assert all(step.sensitivity == Sensitivity.READ for step in plan.steps)
    assert any("network" in step.summary.lower() for step in plan.steps)
    assert "read-only" in plan.rationale.lower()


def test_format_table_is_not_treated_as_destructive():
    planner = GoalPlanner()
    plan = planner._plan_from_provider_json(
        "list folders",
        {
            "rationale": "list",
            "steps": [
                {
                    "adapter": "terminal",
                    "action": "run_powershell",
                    "args": {
                        "command": (
                            "Get-ChildItem C:\\ -Directory | "
                            "ForEach-Object { (Get-ChildItem $_.FullName -Recurse -ErrorAction SilentlyContinue | "
                            "Measure-Object -Property Length -Sum).Sum / 1GB } | Format-Table"
                        ),
                        "timeout_seconds": 60,
                    },
                    "summary": "folder sizes",
                    "sensitivity": "destructive",
                    "side_effects": ["none"],
                }
            ],
        },
    )
    assert plan is not None
    assert plan.steps[0].sensitivity == Sensitivity.READ
    assert int(plan.steps[0].args["timeout_seconds"]) >= 300


def test_run_tests_journey_uses_pytest():
    runtime = _runtime()
    plan = runtime.planner.plan("run pytest")
    assert "pytest" in plan.rationale.lower()
    assert plan.steps[0].sensitivity == Sensitivity.READ
    assert plan.steps[1].sensitivity == Sensitivity.MUTATE
    assert all("pytest" in str(step.args.get("command", "")).lower() for step in plan.steps)
    assert not any(step.sensitivity == Sensitivity.DESTRUCTIVE for step in plan.steps)


def test_run_tests_does_not_fall_through_to_generic_shell():
    runtime = _runtime()
    plan = runtime.planner.plan("run tests")
    command = str(plan.steps[-1].args.get("command", ""))
    assert "pytest" in command.lower()
    assert "Get-Date" not in command


def test_remove_item_stays_destructive():
    runtime = _runtime()
    plan = runtime.planner.plan("run Remove-Item -Recurse C:\\temp\\demo")
    assert plan.steps[0].sensitivity == Sensitivity.DESTRUCTIVE


def test_diagnostic_alt_phrasing():
    runtime = _runtime()
    plan = runtime.planner.plan("why is my pc slow and low disk")
    assert all(step.sensitivity == Sensitivity.READ for step in plan.steps)


def test_broker_blocks_unapproved_mutate(tmp_path: Path):
    runtime = _runtime(tmp_path)
    plan = runtime.planner.plan("start my workday")
    decision = ApprovalDecision(
        plan_id=plan.id,
        approved_step_ids=frozenset(),
        rejected_step_ids=frozenset(step.id for step in plan.steps),
    )
    results = runtime.broker.execute_plan(plan, decision, dry_run=True, use_trusted_match=False)
    assert results
    assert any(not r.ok for r in results)


def test_broker_allows_approved_dry_run(tmp_path: Path):
    runtime = _runtime(tmp_path)
    plan = runtime.planner.plan("list files in ~/Downloads")
    decision = approve_all(plan)
    results = runtime.broker.execute_plan(plan, decision, dry_run=True)
    assert results
    assert all(r.ok for r in results)
    assert all(r.dry_run for r in results)


def test_hard_confirmation_required_for_destructive(tmp_path: Path):
    runtime = _runtime(tmp_path)
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
    runtime = _runtime(tmp_path)
    plan = runtime.planner.plan("list files in ~/Downloads")
    decision = approve_all(plan, promote_to_trusted=True, trusted_name="list-downloads")
    runtime.broker.execute_plan(plan, decision, dry_run=True)
    routines = runtime.broker.list_routines()
    assert len(routines) == 1
    assert routines[0].name == "list-downloads"
    assert runtime.broker.revoke_routine(routines[0].id) is True
    assert runtime.broker.list_routines() == []


def test_trusted_routine_skips_reapproval(tmp_path: Path):
    runtime = _runtime(tmp_path)
    plan1 = runtime.planner.plan("list files in ~/Downloads")
    runtime.broker.execute_plan(
        plan1,
        approve_all(plan1, promote_to_trusted=True, trusted_name="list-downloads"),
        dry_run=True,
    )
    persist_routines(runtime)

    # Fresh runtime loads persisted routines.
    runtime2 = _runtime(tmp_path)
    plan2 = runtime2.planner.plan("list files in ~/Downloads")
    matched = runtime2.broker.find_matching_routine(plan2)
    assert matched is not None
    assert matched.name == "list-downloads"

    # Empty approval decision still runs via trusted match.
    empty = ApprovalDecision(
        plan_id=plan2.id,
        approved_step_ids=frozenset(),
        rejected_step_ids=frozenset(step.id for step in plan2.steps),
    )
    results = runtime2.broker.execute_plan(plan2, empty, dry_run=True)
    assert results
    assert all(r.ok for r in results)


def test_provider_json_plan():
    class FakeProvider:
        name = "fake-local"

        def available(self) -> bool:
            return True

        def complete(self, prompt: str) -> str:
            return """
            {
              "rationale": "Read-only check",
              "steps": [
                {
                  "adapter": "files",
                  "action": "list_directory",
                  "args": {"path": "C:\\\\Temp"},
                  "summary": "List Temp",
                  "sensitivity": "read",
                  "side_effects": ["Reads directory listing"]
                }
              ]
            }
            """

    planner = GoalPlanner(provider=FakeProvider())
    plan = planner.plan("show me what is sitting in temp please")
    assert plan.steps
    assert plan.steps[0].adapter == "files"
    assert "[fake-local]" in plan.rationale


def test_memory_roundtrip(tmp_path: Path):
    runtime = _runtime(tmp_path)
    runtime.memory.set("theme", "focus")
    assert runtime.memory.get("theme") == "focus"
    runtime.memory.wipe()
    assert runtime.memory.get("theme") is None


def test_format_plan_includes_steps():
    runtime = _runtime()
    plan = runtime.planner.plan("set up a project")
    text = format_plan(plan)
    assert "Plan " in text
    assert "Steps:" in text
