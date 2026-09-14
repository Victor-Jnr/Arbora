"""CLI: arbora serve — localhost plan-accept HTTP API."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from arbora.api.server import (
    DEFAULT_PORT,
    MIN_TOKEN_LEN,
    ApiSession,
    assert_loopback_host,
    handle_request,
    make_token,
)
from arbora.cli.session import build_runtime


def run_serve(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="arbora serve",
        description=(
            "Localhost HTTP plan-accept API. POST /v1/goals then "
            "POST /v1/plans/{id}/approve. Optional sandbox: POST /v1/execute. "
            "Dry-run default; hard classes need hard_confirm."
        ),
    )
    parser.add_argument("--host", default="127.0.0.1", help="Loopback bind address")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Listen port")
    parser.add_argument(
        "--token",
        default=None,
        help="API token (or ARBORA_API_TOKEN). Generated if omitted.",
    )
    parser.add_argument("--memory-dir", type=Path, default=None, help="Override local memory directory")
    parser.add_argument(
        "--provider",
        default=None,
        help="Model provider: ollama (default), echo, or openai",
    )
    parser.add_argument(
        "--sandbox-auto-execute",
        action="store_true",
        help=(
            "Enable POST /v1/execute (plan + accept non-hard steps in one call). "
            "For isolated lab hosts only. Still loopback, token, dry-run default, "
            "and hard_confirm for hard classes. Also set by ARBORA_SANDBOX_AUTO_EXECUTE=1. "
            "See docs/sandbox.md."
        ),
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        host = assert_loopback_host(str(args.host))
    except ValueError as exc:
        print(exc)
        return 2
    if args.port < 1 or args.port > 65535:
        print("port must be between 1 and 65535")
        return 2

    token = (args.token or os.environ.get("ARBORA_API_TOKEN") or "").strip()
    generated = False
    if not token:
        token = make_token()
        generated = True
    if len(token) < MIN_TOKEN_LEN:
        print(f"API token must be at least {MIN_TOKEN_LEN} characters")
        return 2

    runtime = build_runtime(memory_root=args.memory_dir, provider=args.provider, seed_samples=True)
    sandbox = bool(args.sandbox_auto_execute) or _env_flag("ARBORA_SANDBOX_AUTO_EXECUTE")
    session = ApiSession(runtime=runtime, token=token, sandbox_auto_execute=sandbox)
    httpd = ThreadingHTTPServer((host, int(args.port)), _handler_for(session))
    print(f"Arbora plan-accept API on http://{host}:{args.port}")
    print("POST /v1/goals then POST /v1/plans/{id}/approve  (Authorization: Bearer <token>)")
    if sandbox:
        print("SANDBOX AUTO-EXECUTE is on: POST /v1/execute plans and runs non-hard steps in one call")
        print("Hard classes still need hard_confirm. Dry-run still defaults to true.")
    if generated:
        print(f"API token (shown once): {token}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()
    return 0


def _handler_for(session: ApiSession) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))

        def _handle(self) -> None:
            length = int(self.headers.get("Content-Length") or "0")
            body = self.rfile.read(max(0, length)) if length else b""
            status, payload = handle_request(
                session,
                method=self.command,
                path=self.path,
                headers={key: value for key, value in self.headers.items()},
                body=body,
            )
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:  # noqa: N802
            self._handle()

        def do_POST(self) -> None:  # noqa: N802
            self._handle()

        def do_DELETE(self) -> None:  # noqa: N802
            self._handle()

    return Handler


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}
