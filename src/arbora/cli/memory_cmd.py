"""`arbora memory` — inspect or export encrypted local memory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from arbora.cli.session import build_runtime
from arbora.memory.store import export_memory_payload, memory_status_rows


def run_memory(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect or export Arbora local memory")
    parser.add_argument("--memory-dir", type=Path, default=None, help="Override local memory directory")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show encryption status and stored keys")

    export_parser = sub.add_parser("export", help="Export memory contents as JSON (no encryption keys)")
    export_parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output file (default: stdout)",
    )

    args = parser.parse_args(argv)
    runtime = build_runtime(memory_root=args.memory_dir)

    if args.command == "status":
        for row in memory_status_rows(runtime.memory):
            print(row)
        return 0

    if args.command == "export":
        payload = export_memory_payload(runtime.memory)
        text = json.dumps(payload, indent=2)
        if args.out is None:
            print(text)
            return 0
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {len(payload.get('data', {}))} key(s) to {args.out}")
        return 0

    parser.print_help()
    return 2
