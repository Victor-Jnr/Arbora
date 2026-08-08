"""CLI health check for local Arbora dependencies."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from arbora.setup_status import Light, ServiceStatus, first_run_checklist


def run_doctor(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="arbora doctor",
        description="Probe Memory, Ollama, and Playwright with fix hints.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON (name, light, detail, fix_hint).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    steps = first_run_checklist()
    statuses = [step.status for step in steps]
    if args.json:
        import json

        payload = [
            {
                "name": s.name,
                "light": s.light.value,
                "detail": s.detail,
                "fix_hint": s.fix_hint,
                "required": step.required,
            }
            for step, s in zip(steps, statuses, strict=True)
        ]
        print(json.dumps(payload, indent=2))
        return _exit_code(steps)

    print("Arbora doctor")
    print("=============")
    for step in steps:
        status = step.status
        print(_format_line(status))
        if status.light != Light.GREEN:
            print(f"         fix: {status.fix_hint}")

    print()
    required_blocked = [s for s in steps if s.required and s.status.light == Light.RED]
    if required_blocked:
        print("Required checks failed. See docs/install.md")
    elif any(s.status.light != Light.GREEN for s in steps):
        print("Optional checks need attention. Core chat can still run (try --provider echo).")
    else:
        print("All checks green.")
    return _exit_code(steps)


def _format_line(status: ServiceStatus) -> str:
    mark = {Light.GREEN: "OK", Light.YELLOW: "WARN", Light.RED: "FAIL"}[status.light]
    return f"[{mark:4}] {status.name}: {status.detail}"


def _exit_code(steps) -> int:
    """0 = all green; 1 = required failed; 2 = optional issues / warnings."""
    if any(step.required and step.status.light == Light.RED for step in steps):
        return 1
    if any(step.status.light != Light.GREEN for step in steps):
        return 2
    return 0
