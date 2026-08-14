"""`arbora schedule` — manage time triggers for trusted routines."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from arbora.cli.session import build_runtime
from arbora.schedules.runner import run_due_schedules, run_schedule
from arbora.schedules.store import (
    add_schedule,
    load_schedules,
    remove_schedule,
    schedule_rows,
)


def run_schedule_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage trusted-routine schedules")
    parser.add_argument("--memory-dir", type=Path, default=None, help="Override local memory directory")
    parser.add_argument("--provider", default=None, help="Model provider (ollama, echo, openai)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List saved schedules")

    add_parser = sub.add_parser("add", help="Add a schedule for a trusted routine")
    add_parser.add_argument("routine_id", help="Trusted routine id (see arbora schedule list-routines)")
    add_parser.add_argument("time", help="Daily time HH:MM (24-hour)")
    add_parser.add_argument(
        "--days",
        default=None,
        help="Comma-separated weekdays (mon,tue,...) or omit for every day",
    )
    add_parser.add_argument(
        "--execute",
        action="store_true",
        help="Run live (default schedules use dry-run for safety)",
    )

    remove_parser = sub.add_parser("remove", help="Remove a schedule by id")
    remove_parser.add_argument("schedule_id")

    run_parser = sub.add_parser("run-due", help="Run schedules that are due now")
    run_parser.add_argument(
        "--execute",
        action="store_true",
        help="Override schedule dry-run and execute live",
    )
    run_parser.add_argument(
        "--force",
        metavar="SCHEDULE_ID",
        help="Run one schedule immediately (ignores due time, still requires trusted match)",
    )

    sub.add_parser("list-routines", help="List trusted routines (for schedule add)")

    args = parser.parse_args(argv)
    runtime = build_runtime(memory_root=args.memory_dir, provider=args.provider)

    if args.command == "list-routines":
        routines = runtime.broker.list_routines()
        if not routines:
            print("(no trusted routines)")
            return 0
        for routine in routines:
            goal = f" goal={routine.goal_norm!r}" if routine.goal_norm else ""
            print(f"  {routine.id}  {routine.name}{goal}")
        return 0

    if args.command == "list":
        schedules = load_schedules(runtime.memory)
        if not schedules:
            print("(no schedules)")
            return 0
        names = {routine.id: routine.name for routine in runtime.broker.list_routines()}
        for row in schedule_rows(schedules, routine_names=names):
            print(f"  {row}")
        return 0

    if args.command == "add":
        routines = {routine.id: routine for routine in runtime.broker.list_routines()}
        if args.routine_id not in routines:
            print(f"Trusted routine not found: {args.routine_id}", file=sys.stderr)
            print("Use `arbora schedule list-routines` to see valid ids.", file=sys.stderr)
            return 1
        schedule = add_schedule(
            runtime.memory,
            routine_id=args.routine_id,
            time_hhmm=args.time,
            days=args.days,
            dry_run=not args.execute,
        )
        print(f"Added schedule {schedule.id} for routine {routines[args.routine_id].name}")
        return 0

    if args.command == "remove":
        ok = remove_schedule(runtime.memory, args.schedule_id)
        print("Removed." if ok else "Schedule not found.")
        return 0 if ok else 1

    if args.command == "run-due":
        if args.force:
            schedules = {schedule.id: schedule for schedule in load_schedules(runtime.memory)}
            schedule = schedules.get(args.force)
            if schedule is None:
                print(f"Schedule not found: {args.force}", file=sys.stderr)
                return 1
            dry_run = False if args.execute else None
            result = run_schedule(runtime, schedule, dry_run=dry_run)
            _print_run_results([result])
            return 0 if result.ok or result.skipped else 1

        dry_run = False if args.execute else None
        results = run_due_schedules(runtime, dry_run=dry_run)
        if not results:
            print("(no schedules due)")
            return 0
        _print_run_results(results)
        return 0 if all(result.ok or result.skipped for result in results) else 1

    parser.print_help()
    return 2


def _print_run_results(results: list) -> None:
    for result in results:
        status = "skipped" if result.skipped else ("ok" if result.ok else "failed")
        print(f"{result.schedule_id}: {status} — {result.message}")
        if result.report is not None:
            print(json.dumps({"plan_id": result.report.plan_id, "all_ok": result.report.all_ok}))
