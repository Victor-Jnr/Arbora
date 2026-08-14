"""Interactive chat shell: plan → approve → execute."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from arbora import __version__
from arbora.cli.session import (
    approve_all,
    build_runtime,
    format_plan,
    hard_confirm_ids_for,
    persist_routines,
    provider_privacy_notice,
)
from arbora.core.types import ApprovalDecision, ExecutionReport
from arbora.providers.ollama import DEFAULT_MODEL
from arbora.schedules.store import load_schedules, schedule_rows
from arbora.workflows.packs import load_workflow_packs, workflow_pack_rows


BANNER = f"""
Arbora v{__version__} — Stage 1 prototype
Models propose; the permission broker disposes.

Commands:
  arbora doctor   Probe Memory / Ollama / Playwright (fix hints)
  /help           Show help
  /audit          Show recent audit events
  /routines       List trusted routines
  /revoke ID      Revoke a trusted routine
  /provider       Show active model provider
  /memory         Show local memory encryption status
  /wipe           Wipe local memory (routines/preferences)
  /workflows      List reusable workflow packs
  /schedules      List trusted-routine schedules
  /undo           Undo the last organise move batch (shortcut plan)
  /dry on|off     Toggle dry-run mode (default: on)
  /quit           Exit

Try goals like:
  start my workday
  diagnose disk space
  set up a project
  organise my downloads
  undo last organise
  list downloads
  disk diagnose pack
""".strip()


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "doctor":
        from arbora.cli.doctor import run_doctor

        return run_doctor(argv[1:])
    if argv and argv[0] == "schedule":
        from arbora.cli.schedule import run_schedule_cli

        return run_schedule_cli(argv[1:])

    parser = argparse.ArgumentParser(description="Arbora personal assistant (prototype)")
    parser.add_argument("--goal", help="Run a single goal non-interactively")
    parser.add_argument("--yes", action="store_true", help="Auto-approve non-sensitive steps")
    parser.add_argument("--hard-yes", action="store_true", help="Also hard-confirm sensitive steps")
    parser.add_argument("--execute", action="store_true", help="Disable dry-run (actually perform actions)")
    parser.add_argument("--promote", metavar="NAME", help="Promote successful plan to a trusted routine")
    parser.add_argument("--memory-dir", type=Path, default=None, help="Override local memory directory")
    parser.add_argument(
        "--provider",
        default=None,
        help="Model provider: ollama (default), echo, or openai (requires ARBORA_OPENAI_API_KEY)",
    )
    args = parser.parse_args(argv)

    runtime = build_runtime(memory_root=args.memory_dir, provider=args.provider)
    dry_run = not args.execute

    if args.goal:
        return _run_once(
            runtime,
            args.goal,
            dry_run=dry_run,
            auto_approve=args.yes,
            hard_confirm=args.hard_yes,
            promote_name=args.promote,
        )

    print(BANNER)
    print(f"\nProvider: {runtime.provider_name}")
    notice = provider_privacy_notice(runtime.planner._provider)  # noqa: SLF001
    if notice:
        print(f"Privacy: {notice}")
    if runtime.provider_name == "ollama":
        print(f"Ollama model default: {DEFAULT_MODEL} (override with ARBORA_OLLAMA_MODEL)")
    print(
        f"Memory: encrypted at rest ({runtime.memory.key_backend} key) under {runtime.memory.root}"
    )
    print(f"Dry-run mode: {'ON' if dry_run else 'OFF (live execution)'}\n")

    while True:
        try:
            raw = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return 0

        if not raw:
            continue

        if raw.startswith("/"):
            dry_run, should_quit = _handle_command(runtime, raw, dry_run)
            if should_quit:
                return 0
            continue

        plan = runtime.planner.plan(raw)
        runtime.audit.record("plan_created", plan.rationale or plan.goal, plan_id=plan.id, goal=raw)
        matched = runtime.broker.find_matching_routine(plan)
        print()
        print(format_plan(plan))
        print()

        if matched is not None:
            print(f"Trusted routine matched: '{matched.name}' — skipping re-approval.")
            hard_ids = frozenset()
            if plan.has_hard_confirmation_steps:
                print("Hard-confirmation steps still require an explicit yes.")
                if _confirm("Confirm sensitive steps? [y/N] "):
                    hard_ids = hard_confirm_ids_for(plan, True)
                else:
                    hard_step_ids = {s.id for s in plan.steps if s.requires_hard_confirmation()}
                    decision = ApprovalDecision(
                        plan_id=plan.id,
                        approved_step_ids=frozenset(s.id for s in plan.steps if s.id not in hard_step_ids),
                        rejected_step_ids=frozenset(hard_step_ids),
                    )
                    results = runtime.broker.execute_plan(
                        plan, decision, dry_run=dry_run, hard_confirmed_step_ids=frozenset()
                    )
                    _print_report(ExecutionReport(plan_id=plan.id, results=results))
                    continue

            decision = approve_all(plan)
            results = runtime.broker.execute_plan(
                plan, decision, dry_run=dry_run, hard_confirmed_step_ids=hard_ids
            )
            _print_report(ExecutionReport(plan_id=plan.id, results=results))
            runtime.memory.set("last_goal", raw)
            runtime.memory.set("last_plan_id", plan.id)
            continue

        if not _confirm("Approve this plan? [y/N] "):
            runtime.audit.record("plan_rejected", "User rejected plan", plan_id=plan.id)
            print("Plan rejected.\n")
            continue

        hard_ids = frozenset()
        if plan.has_hard_confirmation_steps:
            print("This plan includes HARD CONFIRMATION steps (destructive/credential/financial).")
            if _confirm("Explicitly confirm those sensitive steps? [y/N] "):
                hard_ids = hard_confirm_ids_for(plan, True)
            else:
                hard_step_ids = {s.id for s in plan.steps if s.requires_hard_confirmation()}
                decision = ApprovalDecision(
                    plan_id=plan.id,
                    approved_step_ids=frozenset(s.id for s in plan.steps if s.id not in hard_step_ids),
                    rejected_step_ids=frozenset(hard_step_ids),
                )
                results = runtime.broker.execute_plan(
                    plan, decision, dry_run=dry_run, hard_confirmed_step_ids=frozenset()
                )
                _print_report(ExecutionReport(plan_id=plan.id, results=results))
                continue

        promote = False
        promote_name = None
        if _confirm("Promote to a trusted routine after success? [y/N] "):
            promote = True
            promote_name = input("Routine name> ").strip() or "unnamed-routine"

        decision = approve_all(plan, promote_to_trusted=promote, trusted_name=promote_name)
        results = runtime.broker.execute_plan(
            plan, decision, dry_run=dry_run, hard_confirmed_step_ids=hard_ids
        )
        report = ExecutionReport(plan_id=plan.id, results=results)
        _print_report(report)
        if promote:
            persist_routines(runtime)
        runtime.memory.set("last_goal", raw)
        runtime.memory.set("last_plan_id", plan.id)


def _run_once(runtime, goal: str, *, dry_run: bool, auto_approve: bool, hard_confirm: bool, promote_name: str | None) -> int:
    plan = runtime.planner.plan(goal)
    matched = runtime.broker.find_matching_routine(plan)
    print(format_plan(plan))
    if matched is not None:
        print(f"\nTrusted routine matched: '{matched.name}' — running without --yes.")
    elif not auto_approve:
        print("\nRefusing to execute without --yes in non-interactive mode.")
        return 2

    hard_ids = hard_confirm_ids_for(plan, hard_confirm)
    if plan.has_hard_confirmation_steps and not hard_confirm:
        hard_step_ids = {s.id for s in plan.steps if s.requires_hard_confirmation()}
        decision = ApprovalDecision(
            plan_id=plan.id,
            approved_step_ids=frozenset(s.id for s in plan.steps if s.id not in hard_step_ids),
            rejected_step_ids=frozenset(hard_step_ids),
            promote_to_trusted=False,
        )
    else:
        decision = approve_all(
            plan,
            promote_to_trusted=promote_name is not None and matched is None,
            trusted_name=promote_name,
        )

    results = runtime.broker.execute_plan(
        plan, decision, dry_run=dry_run, hard_confirmed_step_ids=hard_ids
    )
    report = ExecutionReport(plan_id=plan.id, results=results)
    if promote_name and matched is None:
        persist_routines(runtime)
    _print_report(report)
    return 0 if report.all_ok else 1


def _handle_command(runtime, raw: str, dry_run: bool) -> tuple[bool, bool]:
    parts = raw.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd in {"/quit", "/exit", "/q"}:
        print("Bye.")
        return dry_run, True
    if cmd == "/help":
        print(BANNER)
        return dry_run, False
    if cmd == "/provider":
        print(f"Active provider: {runtime.provider_name}")
        notice = provider_privacy_notice(runtime.planner._provider)  # noqa: SLF001
        if notice:
            print(f"Privacy: {notice}")
        return dry_run, False
    if cmd == "/memory":
        print(f"Root: {runtime.memory.root}")
        print(f"Encrypted at rest: {runtime.memory.encrypted_at_rest}")
        print(f"Key backend: {runtime.memory.key_backend}")
        print(f"Keys in store: {len(runtime.memory.export())}")
        return dry_run, False
    if cmd == "/wipe":
        if not _confirm("Wipe local memory (preferences + trusted routines)? [y/N] "):
            print("Cancelled.")
            return dry_run, False
        runtime.memory.wipe()
        runtime.broker.load_routines([])
        print("Local memory wiped.")
        return dry_run, False
    if cmd == "/audit":
        events = runtime.audit.events()[-20:]
        if not events:
            print("(audit log empty)")
        for event in events:
            print(f"[{event.created_at.isoformat(timespec='seconds')}] {event.kind}: {event.message}")
        return dry_run, False
    if cmd == "/routines":
        routines = runtime.broker.list_routines()
        if not routines:
            print("(no trusted routines)")
        for routine in routines:
            goal = f" goal={routine.goal_norm!r}" if routine.goal_norm else ""
            print(f"  {routine.id}  {routine.name}  fp={routine.plan_fingerprint}  v{routine.version}{goal}")
        return dry_run, False
    if cmd == "/revoke":
        if not arg:
            print("Usage: /revoke ROUTINE_ID")
            return dry_run, False
        ok = runtime.broker.revoke_routine(arg)
        if ok:
            persist_routines(runtime)
        print("Revoked." if ok else "Routine not found.")
        return dry_run, False
    if cmd == "/workflows":
        rows = workflow_pack_rows(load_workflow_packs())
        if not rows:
            print("(no workflow packs found)")
        else:
            print("Workflow packs:")
            for row in rows:
                print(f"  {row}")
        return dry_run, False
    if cmd == "/schedules":
        schedules = load_schedules(runtime.memory)
        if not schedules:
            print("(no schedules — use `arbora schedule add`)")
            return dry_run, False
        names = {routine.id: routine.name for routine in runtime.broker.list_routines()}
        print("Trusted-routine schedules:")
        for row in schedule_rows(schedules, routine_names=names):
            print(f"  {row}")
        return dry_run, False
    if cmd == "/undo":
        plan = runtime.planner.plan("undo last organise")
        runtime.audit.record("plan_created", plan.rationale or plan.goal, plan_id=plan.id, goal="undo last organise")
        print()
        print(format_plan(plan))
        print()
        if not _confirm("Approve undo plan? [y/N] "):
            print("Undo cancelled.\n")
            return dry_run, False
        decision = approve_all(plan)
        results = runtime.broker.execute_plan(plan, decision, dry_run=dry_run)
        _print_report(ExecutionReport(plan_id=plan.id, results=results))
        return dry_run, False
    if cmd == "/dry":
        if arg.lower() == "on":
            print("Dry-run ON")
            return True, False
        if arg.lower() == "off":
            print("Dry-run OFF — actions will execute for real")
            return False, False
        print(f"Dry-run is currently {'ON' if dry_run else 'OFF'}. Use /dry on|off")
        return dry_run, False

    print(f"Unknown command: {cmd}. Try /help")
    return dry_run, False


def _confirm(prompt: str) -> bool:
    answer = input(prompt).strip().lower()
    return answer in {"y", "yes"}


def _print_report(report: ExecutionReport) -> None:
    print("\nExecution report:")
    for result in report.results:
        status = "OK" if result.ok else "FAIL"
        mode = "dry-run" if result.dry_run else "live"
        print(f"  [{status}/{mode}] step={result.step_id}")
        if result.output:
            for line in result.output.splitlines()[:30]:
                print(f"    {line}")
        if result.error:
            print(f"    error: {result.error}")
    print(f"Overall: {'success' if report.all_ok else 'completed with failures'}\n")


if __name__ == "__main__":
    sys.exit(main())
