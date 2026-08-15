"""MVP exit-criteria validation for early testers."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from arbora.cli.session import approve_all, build_runtime, persist_routines
from arbora.providers import cloud_provider_configured


@dataclass
class ValidateCheck:
    id: str
    title: str
    ok: bool
    detail: str


MVP_JOURNEY_GOALS = (
    ("workday_journey", "Workday setup journey", "start my workday"),
    ("diagnose_journey", "PC diagnostic journey", "diagnose disk space"),
    ("dev_setup_journey", "Developer project setup journey", "set up a project"),
)


def run_validate(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="arbora validate",
        description="Dry-run checks for Stage 2 MVP exit criteria.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON results.",
    )
    parser.add_argument(
        "--memory-dir",
        type=Path,
        default=None,
        help="Override local memory directory (uses a temp dir by default)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    with tempfile.TemporaryDirectory() as tmp:
        memory_root = args.memory_dir or Path(tmp)
        checks = run_mvp_checks(memory_root=memory_root)

    if args.json:
        payload = [
            {"id": check.id, "title": check.title, "ok": check.ok, "detail": check.detail}
            for check in checks
        ]
        print(json.dumps(payload, indent=2))
    else:
        print("Arbora MVP validate")
        print("===================")
        for check in checks:
            mark = "ok" if check.ok else "FAIL"
            print(f"[{mark}] {check.title}")
            print(f"      {check.detail}")
        print()
        passed = sum(1 for check in checks if check.ok)
        print(f"{passed}/{len(checks)} checks passed.")

    return 0 if all(check.ok for check in checks) else 1


def run_mvp_checks(*, memory_root: Path) -> list[ValidateCheck]:
    checks: list[ValidateCheck] = []
    runtime = build_runtime(memory_root=memory_root, provider="echo")

    for check_id, title, goal in MVP_JOURNEY_GOALS:
        checks.append(_journey_check(runtime, check_id, title, goal))

    checks.append(_trust_and_audit_check(runtime))
    checks.append(_local_first_check(runtime))
    return checks


def _journey_check(runtime, check_id: str, title: str, goal: str) -> ValidateCheck:
    try:
        plan = runtime.planner.plan(goal)
        if not plan.steps:
            return ValidateCheck(check_id, title, False, "Planner returned an empty plan.")
        decision = approve_all(plan)
        results = runtime.broker.execute_plan(plan, decision, dry_run=True)
        if not all(result.ok for result in results):
            failed = [result.step_id for result in results if not result.ok]
            return ValidateCheck(
                check_id,
                title,
                False,
                f"Dry-run failed for steps: {', '.join(failed)}",
            )
        return ValidateCheck(
            check_id,
            title,
            True,
            f"Plan {plan.id} with {len(plan.steps)} step(s) dry-ran successfully.",
        )
    except Exception as exc:  # noqa: BLE001 — validation should report, not crash
        return ValidateCheck(check_id, title, False, str(exc))


def _trust_and_audit_check(runtime) -> ValidateCheck:
    check_id = "trust_and_audit"
    title = "Trust UX: promote, audit, revoke"
    try:
        plan = runtime.planner.plan("list files in ~/Downloads")
        runtime.broker.execute_plan(
            plan,
            approve_all(plan, promote_to_trusted=True, trusted_name="mvp-list-downloads"),
            dry_run=True,
        )
        persist_routines(runtime)
        routines = runtime.broker.list_routines()
        if not routines:
            return ValidateCheck(check_id, title, False, "Trusted routine was not created.")

        events_before = len(runtime.audit.events())
        runtime.audit.record("mvp_validate", "trust check marker")
        if len(runtime.audit.events()) <= events_before:
            return ValidateCheck(check_id, title, False, "Audit log did not record events.")

        routine_id = routines[0].id
        if not runtime.broker.revoke_routine(routine_id):
            return ValidateCheck(check_id, title, False, "Failed to revoke trusted routine.")
        persist_routines(runtime)
        if runtime.broker.list_routines():
            return ValidateCheck(check_id, title, False, "Routine still present after revoke.")

        runtime2 = build_runtime(memory_root=runtime.memory.root, provider="echo")
        if not any(event.kind == "mvp_validate" for event in runtime2.audit.events()):
            return ValidateCheck(check_id, title, False, "Audit events did not persist across restart.")

        return ValidateCheck(
            check_id,
            title,
            True,
            "Promoted routine, recorded audit events, revoked, and reloaded persisted audit.",
        )
    except Exception as exc:  # noqa: BLE001
        return ValidateCheck(check_id, title, False, str(exc))


def _local_first_check(runtime) -> ValidateCheck:
    check_id = "local_first"
    title = "Local-first memory with cloud disabled by default"
    try:
        if not runtime.memory.encrypted_at_rest:
            return ValidateCheck(check_id, title, False, "Local memory is not encrypted at rest.")

        provider = (os.environ.get("ARBORA_PROVIDER") or "ollama").strip().lower()
        if provider in {"openai", "cloud"} and not cloud_provider_configured():
            return ValidateCheck(
                check_id,
                title,
                False,
                "ARBORA_PROVIDER points at cloud but no API key is configured.",
            )

        if runtime.provider_name in {"openai", "cloud"}:
            return ValidateCheck(
                check_id,
                title,
                False,
                "Validation ran with a cloud provider; use echo/ollama for local-first default.",
            )

        return ValidateCheck(
            check_id,
            title,
            True,
            f"Encrypted memory under {runtime.memory.root}; provider={runtime.provider_name}.",
        )
    except Exception as exc:  # noqa: BLE001
        return ValidateCheck(check_id, title, False, str(exc))
