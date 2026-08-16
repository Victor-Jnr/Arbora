"""`arbora audit` — export persisted audit events."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from arbora.cli.session import build_runtime
from arbora.core.audit_store import export_audit_payload


def run_audit(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export Arbora audit events")
    parser.add_argument("--memory-dir", type=Path, default=None, help="Override local memory directory")
    sub = parser.add_subparsers(dest="command", required=True)

    export_parser = sub.add_parser("export", help="Export audit events as JSON")
    export_parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output file (default: stdout)",
    )
    export_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Export only the most recent N events",
    )

    args = parser.parse_args(argv)
    runtime = build_runtime(memory_root=args.memory_dir)

    if args.command == "export":
        payload = export_audit_payload(runtime.memory, limit=args.limit)
        text = json.dumps(payload, indent=2)
        if args.out is None:
            print(text)
            return 0
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {len(payload)} event(s) to {args.out}")
        return 0

    parser.print_help()
    return 2
