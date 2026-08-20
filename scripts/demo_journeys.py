"""Smoke-run priority journeys in dry-run mode."""

from __future__ import annotations

from pathlib import Path
import tempfile

from arbora.cli.session import approve_all, build_runtime, format_plan


GOALS = [
    "start my workday",
    "diagnose disk space",
    "what folder is using the most storage on C",
    "run pytest",
    "set up a project",
    "organise my downloads",
]


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        runtime = build_runtime(memory_root=Path(tmp), provider="echo")
        for goal in GOALS:
            plan = runtime.planner.plan(goal)
            print("=" * 60)
            print(format_plan(plan))
            decision = approve_all(plan)
            results = runtime.broker.execute_plan(plan, decision, dry_run=True)
            for result in results:
                status = "OK" if result.ok else "FAIL"
                print(f"  [{status}] {result.output or result.error}")
            print()


if __name__ == "__main__":
    main()
