"""Tests for the localhost plan-accept HTTP API."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from arbora.api.server import ApiSession, assert_loopback_host, handle_request, make_token
from arbora.cli.session import build_runtime
from arbora.core.types import Sensitivity
from arbora.setup_status import FirstRunStep, Light, ServiceStatus


def _session(tmp_path: Path, token: str = "arbora-test-token-1") -> ApiSession:
    runtime = build_runtime(memory_root=tmp_path / "memory", provider="echo")
    return ApiSession(runtime=runtime, token=token)


def _headers(token: str = "arbora-test-token-1") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _call(session: ApiSession, method: str, path: str, payload: dict | None = None, headers: dict | None = None):
    body = b""
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    return handle_request(
        session,
        method=method,
        path=path,
        headers=_headers() if headers is None else headers,
        body=body,
    )


def test_assert_loopback_host_accepts_localhost():
    assert assert_loopback_host("127.0.0.1") == "127.0.0.1"
    assert assert_loopback_host("localhost") == "127.0.0.1"
    assert assert_loopback_host("::1") == "::1"


def test_assert_loopback_host_rejects_wildcard():
    try:
        assert_loopback_host("0.0.0.0")
    except ValueError as exc:
        assert "loopback" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError")


def test_missing_token_is_rejected(tmp_path: Path):
    session = _session(tmp_path)
    status, payload = _call(session, "GET", "/v1/health", headers={})
    assert status == 401
    assert "token" in payload["error"].lower()


def test_health_requires_token_and_returns_doctor_rows(tmp_path: Path):
    session = _session(tmp_path)
    fake = [
        FirstRunStep(
            "memory",
            "Encrypted local memory",
            ServiceStatus("Memory", Light.GREEN, "ok"),
            required=True,
        )
    ]
    with patch("arbora.cli.doctor.first_run_checklist", return_value=fake):
        status, payload = _call(session, "GET", "/v1/health")
    assert status == 200
    assert payload["checks"][0]["name"] == "Memory"
    assert payload["checks"][0]["light"] == "green"


def test_goals_reject_auto_approve(tmp_path: Path):
    session = _session(tmp_path)
    status, payload = _call(
        session,
        "POST",
        "/v1/goals",
        {"goal": "windows version", "auto_approve": True},
    )
    assert status == 400
    assert "approve" in payload["error"].lower()


def test_create_plan_then_accept_all_non_hard_dry_run(tmp_path: Path):
    session = _session(tmp_path)
    status, created = _call(session, "POST", "/v1/goals", {"goal": "windows version"})
    assert status == 200
    assert created["accepted"] is False
    assert created["dry_run"] is True
    plan = created["plan"]
    assert plan["steps"][0]["action"] == "inspect_windows_version"
    assert plan["steps"][0]["sensitivity"] == Sensitivity.READ.value
    plan_id = plan["id"]

    status, denied = _call(session, "POST", f"/v1/plans/{plan_id}/approve", {})
    assert status == 400
    assert "acceptance required" in denied["error"].lower()

    status, report = _call(
        session,
        "POST",
        f"/v1/plans/{plan_id}/approve",
        {"accept_all_non_hard": True},
    )
    assert status == 200
    assert report["dry_run"] is True
    assert report["results"][0]["ok"] is True
    assert report["results"][0]["dry_run"] is True
    assert "productkey" in report["results"][0]["output"].lower()

    status, missing = _call(
        session,
        "POST",
        f"/v1/plans/{plan_id}/approve",
        {"accept_all_non_hard": True},
    )
    assert status == 404


def test_hard_steps_need_hard_confirm(tmp_path: Path):
    session = _session(tmp_path)
    status, created = _call(session, "POST", "/v1/goals", {"goal": "empty the recycle bin"})
    assert status == 200
    plan = created["plan"]
    assert plan["has_hard_confirmation_steps"] is True
    hard_ids = [step["id"] for step in plan["steps"] if step["requires_hard_confirmation"]]
    assert hard_ids
    plan_id = plan["id"]

    status, report = _call(
        session,
        "POST",
        f"/v1/plans/{plan_id}/approve",
        {"accept_all_non_hard": True, "approved_step_ids": hard_ids},
    )
    assert status == 200
    hard_results = [item for item in report["results"] if item["step_id"] in hard_ids]
    assert hard_results
    assert all(item["ok"] is False for item in hard_results)
    assert any("hard confirmation" in (item["error"] or "").lower() for item in hard_results)


def test_explicit_step_ids_are_accepted(tmp_path: Path):
    session = _session(tmp_path)
    _, created = _call(session, "POST", "/v1/goals", {"goal": "pending reboot"})
    step_id = created["plan"]["steps"][0]["id"]
    status, report = _call(
        session,
        "POST",
        f"/v1/plans/{created['plan']['id']}/approve",
        {"approved_step_ids": [step_id]},
    )
    assert status == 200
    assert report["results"][0]["ok"] is True


def test_make_token_is_long_enough():
    token = make_token()
    assert len(token) >= 16


def test_run_serve_rejects_non_loopback():
    from arbora.cli.serve import run_serve

    assert run_serve(["--host", "0.0.0.0", "--token", "arbora-test-token-1"]) == 2


def test_main_dispatches_serve():
    from arbora.cli.main import main

    with patch("arbora.cli.serve.run_serve", return_value=0) as serve:
        assert main(["serve", "--help"]) == 0
        serve.assert_called_once_with(["--help"])
