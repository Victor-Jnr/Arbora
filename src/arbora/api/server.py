"""Token-gated loopback HTTP for plan → accept → execute.

Callers POST /v1/goals to create a plan, then POST /v1/plans/{id}/approve
to accept steps. The permission broker still authorises every adapter call.
Hard-confirmation classes still need hard_confirm. Dry-run is the default.
"""

from __future__ import annotations

import hmac
import json
import secrets
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from arbora.cli.doctor import doctor_payload
from arbora.cli.session import Runtime, persist_routines
from arbora.core.audit_store import export_audit_payload
from arbora.core.routines_store import routines_to_dicts
from arbora.core.types import ApprovalDecision, Plan, TrustedRoutine
from arbora.memory.goal_history import record_goal

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
MAX_BODY_BYTES = 65536
MAX_PENDING = 32
MAX_RESULT_CHARS = 8000
MIN_TOKEN_LEN = 16
DEFAULT_PORT = 8472


class ApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass
class PendingPlan:
    plan: Plan
    dry_run: bool
    trusted_match: TrustedRoutine | None


@dataclass
class ApiSession:
    runtime: Runtime
    token: str
    pending: dict[str, PendingPlan] = field(default_factory=dict)


def make_token() -> str:
    return secrets.token_urlsafe(32)


def assert_loopback_host(host: str) -> str:
    cleaned = (host or "").strip().lower()
    if cleaned not in LOOPBACK_HOSTS:
        raise ValueError("API bind host must be loopback (127.0.0.1, localhost, or ::1)")
    if cleaned == "localhost":
        return "127.0.0.1"
    return (host or "").strip()


def handle_request(
    session: ApiSession,
    *,
    method: str,
    path: str,
    headers: Mapping[str, str],
    body: bytes,
) -> tuple[int, dict[str, Any]]:
    """Dispatch one API call. Returns (status_code, JSON object)."""
    try:
        return _dispatch(session, method=method, path=path, headers=headers, body=body)
    except ApiError as exc:
        return exc.status, {"error": exc.message}


def _dispatch(
    session: ApiSession,
    *,
    method: str,
    path: str,
    headers: Mapping[str, str],
    body: bytes,
) -> tuple[int, dict[str, Any]]:
    if len(body) > MAX_BODY_BYTES:
        raise ApiError(413, "Request body too large")
    method = method.upper()
    route = path.split("?", 1)[0].rstrip("/") or "/"
    _require_token(session, headers)

    if method == "GET" and route == "/v1/health":
        return 200, {"checks": doctor_payload()}
    if method == "POST" and route == "/v1/goals":
        return 200, _create_plan(session, _read_json(body))
    if method == "GET" and route == "/v1/audit":
        return 200, {"events": export_audit_payload(session.runtime.memory, limit=100)}
    if method == "GET" and route == "/v1/routines":
        return 200, {"routines": routines_to_dicts(session.runtime.broker.list_routines())}
    if method == "GET" and route.startswith("/v1/plans/"):
        plan_id = route.removeprefix("/v1/plans/").split("/", 1)[0]
        if "/" in route.removeprefix("/v1/plans/"):
            raise ApiError(404, "Unknown path")
        return 200, _get_pending(session, plan_id)
    if method == "POST" and route.startswith("/v1/plans/") and route.endswith("/approve"):
        plan_id = route.removeprefix("/v1/plans/").removesuffix("/approve").strip("/")
        if not plan_id or "/" in plan_id:
            raise ApiError(404, "Unknown path")
        return 200, _approve_plan(session, plan_id, _read_json(body))
    if method == "DELETE" and route.startswith("/v1/routines/"):
        routine_id = route.removeprefix("/v1/routines/")
        if not routine_id or "/" in routine_id:
            raise ApiError(404, "Unknown path")
        return 200, _revoke_routine(session, routine_id)
    if route.startswith("/v1/"):
        raise ApiError(405, f"Method {method} not allowed for {route}")
    raise ApiError(404, "Unknown path")


def _header(headers: Mapping[str, str], name: str) -> str:
    wanted = name.lower()
    for key, value in headers.items():
        if key.lower() == wanted:
            return str(value)
    return ""


def _require_token(session: ApiSession, headers: Mapping[str, str]) -> None:
    presented = ""
    auth = _header(headers, "Authorization")
    if auth.lower().startswith("bearer "):
        presented = auth.split(" ", 1)[1].strip()
    if not presented:
        presented = _header(headers, "X-Arbora-Token").strip()
    expected = session.token or ""
    if len(expected) < MIN_TOKEN_LEN:
        raise ApiError(500, "Server token is not configured")
    left = presented.encode("utf-8")
    right = expected.encode("utf-8")
    if len(left) != len(right) or not hmac.compare_digest(left, right):
        raise ApiError(401, "Invalid or missing API token")


def _read_json(body: bytes) -> dict[str, Any]:
    if not body or not body.strip():
        return {}
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ApiError(400, "Request body must be JSON") from exc
    if not isinstance(payload, dict):
        raise ApiError(400, "JSON object required")
    return payload


def _plan_to_dict(plan: Plan) -> dict[str, Any]:
    return {
        "id": plan.id,
        "goal": plan.goal,
        "rationale": plan.rationale,
        "has_hard_confirmation_steps": plan.has_hard_confirmation_steps,
        "steps": [
            {
                "id": step.id,
                "adapter": step.adapter,
                "action": step.action,
                "args": step.args,
                "summary": step.summary,
                "sensitivity": step.sensitivity.value,
                "side_effects": list(step.side_effects),
                "requires_hard_confirmation": step.requires_hard_confirmation(),
            }
            for step in plan.steps
        ],
    }


def _trusted_to_dict(routine: TrustedRoutine | None) -> dict[str, Any] | None:
    if routine is None:
        return None
    return {
        "id": routine.id,
        "name": routine.name,
        "enabled": routine.enabled,
    }


def _store_pending(session: ApiSession, pending: PendingPlan) -> None:
    session.pending[pending.plan.id] = pending
    overflow = list(session.pending)[:-MAX_PENDING]
    for plan_id in overflow:
        session.pending.pop(plan_id, None)


def _create_plan(session: ApiSession, payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("auto_approve") is True:
        raise ApiError(
            400,
            "auto_approve is not accepted; POST /v1/plans/{id}/approve to accept steps",
        )
    goal = str(payload.get("goal") or "").strip()
    if not goal:
        raise ApiError(400, "goal is required")
    dry_run = bool(payload["dry_run"]) if "dry_run" in payload else True
    plan = session.runtime.planner.plan(goal)
    record_goal(session.runtime.memory, goal)
    session.runtime.audit.record(
        "plan_created",
        plan.rationale or plan.goal,
        plan_id=plan.id,
        goal=goal,
        via="http_api",
    )
    matched = session.runtime.broker.find_matching_routine(plan)
    _store_pending(session, PendingPlan(plan=plan, dry_run=dry_run, trusted_match=matched))
    return {
        "plan": _plan_to_dict(plan),
        "trusted_match": _trusted_to_dict(matched),
        "dry_run": dry_run,
        "accepted": False,
    }


def _get_pending(session: ApiSession, plan_id: str) -> dict[str, Any]:
    pending = session.pending.get(plan_id)
    if pending is None:
        raise ApiError(404, "Unknown or already-accepted plan")
    return {
        "plan": _plan_to_dict(pending.plan),
        "trusted_match": _trusted_to_dict(pending.trusted_match),
        "dry_run": pending.dry_run,
        "accepted": False,
    }


def _approve_plan(session: ApiSession, plan_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    pending = session.pending.get(plan_id)
    if pending is None:
        raise ApiError(404, "Unknown or already-accepted plan")
    plan = pending.plan
    approved_raw = payload.get("approved_step_ids")
    rejected_raw = payload.get("rejected_step_ids")
    if approved_raw is not None and not isinstance(approved_raw, list):
        raise ApiError(400, "approved_step_ids must be a list")
    if rejected_raw is not None and not isinstance(rejected_raw, list):
        raise ApiError(400, "rejected_step_ids must be a list")
    accept_all_non_hard = bool(payload.get("accept_all_non_hard"))
    hard_confirm = bool(payload.get("hard_confirm"))
    promote = str(payload.get("promote") or "").strip() or None
    dry_run = bool(payload["dry_run"]) if "dry_run" in payload else pending.dry_run

    decision = _decision_from_accept(
        plan,
        approved_step_ids=[str(item) for item in (approved_raw or [])],
        rejected_step_ids=[str(item) for item in (rejected_raw or [])],
        accept_all_non_hard=accept_all_non_hard,
        hard_confirm=hard_confirm,
        promote=promote,
    )
    hard_ids = frozenset(step.id for step in plan.steps if step.requires_hard_confirmation())
    hard_confirmed = hard_ids if hard_confirm else frozenset()
    results = session.runtime.broker.execute_plan(
        plan,
        decision,
        dry_run=dry_run,
        hard_confirmed_step_ids=hard_confirmed,
    )
    session.pending.pop(plan_id, None)
    if promote:
        persist_routines(session.runtime)
    session.runtime.audit.record(
        "plan_finished",
        f"Plan {plan.id} finished via http_api",
        plan_id=plan.id,
        via="http_api",
    )
    return {
        "plan_id": plan.id,
        "dry_run": dry_run,
        "results": [
            {
                "step_id": item.step_id,
                "ok": item.ok,
                "output": (item.output or "")[:MAX_RESULT_CHARS],
                "error": item.error,
                "dry_run": item.dry_run,
            }
            for item in results
        ],
    }


def _decision_from_accept(
    plan: Plan,
    *,
    approved_step_ids: list[str],
    rejected_step_ids: list[str],
    accept_all_non_hard: bool,
    hard_confirm: bool,
    promote: str | None,
) -> ApprovalDecision:
    step_ids = {step.id for step in plan.steps}
    hard_ids = {step.id for step in plan.steps if step.requires_hard_confirmation()}
    unknown = (set(approved_step_ids) | set(rejected_step_ids)) - step_ids
    if unknown:
        raise ApiError(400, "Unknown step id")
    approved = set(approved_step_ids)
    rejected = set(rejected_step_ids)
    if accept_all_non_hard:
        approved |= step_ids - hard_ids
        if hard_confirm:
            approved |= hard_ids
    if not hard_confirm:
        leaked_hard = approved & hard_ids
        approved -= leaked_hard
        rejected |= leaked_hard
    leftover = step_ids - approved - rejected
    rejected |= leftover
    if not approved:
        raise ApiError(
            400,
            "Acceptance required: pass approved_step_ids or accept_all_non_hard",
        )
    return ApprovalDecision(
        plan_id=plan.id,
        approved_step_ids=frozenset(approved),
        rejected_step_ids=frozenset(rejected),
        promote_to_trusted=promote is not None,
        trusted_name=promote,
    )


def _revoke_routine(session: ApiSession, routine_id: str) -> dict[str, Any]:
    ok = session.runtime.broker.revoke_routine(routine_id)
    if not ok:
        raise ApiError(404, "Unknown routine")
    persist_routines(session.runtime)
    return {"revoked": True, "id": routine_id}
