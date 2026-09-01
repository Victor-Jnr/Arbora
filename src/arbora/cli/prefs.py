"""`arbora prefs` — manage opt-in user preferences."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from arbora.cli.session import build_runtime
from arbora.preferences.store import load_preferences, preference_rows, set_preference


def run_prefs(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage opt-in Arbora user preferences")
    parser.add_argument("--memory-dir", type=Path, default=None, help="Override local memory directory")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="Show saved preferences")

    set_parser = sub.add_parser("set", help="Set a preference")
    set_parser.add_argument(
        "key",
        help="dry_run | provider | workday_folder | briefs_folder | projects_folder | downloads_folder | notes_folder | screenshots_folder | run_schedules_on_start | spoken_confirmations",
    )
    set_parser.add_argument("value", help="New value")

    args = parser.parse_args(argv)
    runtime = build_runtime(memory_root=args.memory_dir)

    if args.command == "list":
        prefs = load_preferences(runtime.memory)
        for row in preference_rows(prefs):
            print(row)
        return 0

    if args.command == "set":
        try:
            prefs = set_preference(runtime.memory, args.key, args.value)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"Updated {args.key}.")
        for row in preference_rows(prefs):
            print(f"  {row}")
        return 0

    parser.print_help()
    return 2
