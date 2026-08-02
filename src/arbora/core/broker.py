"""Permission broker — the hard gate between intent and side effects.

Design rule from the vision: models propose; the broker disposes.
No tool adapter should be reachable without going through this module.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Protocol

from arbora.core.audit import AuditLog
from arbora.core.types import (
    HARD_CONFIRMATION_CLASSES,
    ApprovalDecision,
    Plan,
    ScopeGrant,
    Sensitivity,
    StepResult,
    ToolStep,
    TrustedRoutine,
    new_id,
)


class ToolAdapter(Protocol):
    """Narrow OS/app integration. Must only be invoked by the broker."""

    name: str

    def execute(self, action: str, args: dict[str, Any], *, dry_run: bool = False) -> StepResult:
        ...


@dataclass
class Authorization:
    allowed: bool
    reason: str
    requires_hard_confirmation: bool = False


def normalize_goal(goal: str) -> str:
    return " ".join(goal.strip().lower().split())


class PermissionBroker:
    """Authorises tool side effects via scopes, trust, and hard confirmations."""

    def __init__(self, audit: AuditLog) -> None:
        self._audit = audit
        self._adapters: dict[str, ToolAdapter] = {}
        self._grants: list[ScopeGrant] = []
        self._routines: dict[str, TrustedRoutine] = {}

    def register_adapter(self, adapter: ToolAdapter) -> None:
        self._adapters[adapter.name] = adapter
        self._audit.record("adapter_registered", f"Registered adapter '{adapter.name}'")

    def grant(self, grant: ScopeGrant) -> None:
        self._grants.append(grant)
        self._audit.record(
            "scope_granted",
            f"Granted {grant.adapter}:{sorted(grant.actions)}",
            grant_id=grant.id,
        )

    def revoke_routine(self, routine_id: str) -> bool:
        routine = self._routines.pop(routine_id, None)
        if routine is None:
            return False
        self._audit.record(
            "routine_revoked",
            f"Revoked trusted routine '{routine.name}'",
            routine_id=routine_id,
        )
        return True

    def list_routines(self) -> list[TrustedRoutine]:
        return list(self._routines.values())

    def load_routines(self, routines: list[TrustedRoutine]) -> None:
        self._routines = {routine.id: routine for routine in routines}

    def fingerprint_plan(self, plan: Plan) -> str:
        payload = [
            {
                "adapter": step.adapter,
                "action": step.action,
                "args": step.args,
                "sensitivity": step.sensitivity.value,
            }
            for step in plan.steps
        ]
        raw = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def find_matching_routine(self, plan: Plan) -> TrustedRoutine | None:
        """Return a trusted routine whose fingerprint matches this plan."""
        fingerprint = self.fingerprint_plan(plan)
        for routine in self._routines.values():
            if routine.enabled and routine.plan_fingerprint == fingerprint:
                return routine
        return None

    def authorize_step(
        self,
        step: ToolStep,
        *,
        approved: bool,
        hard_confirmed: bool = False,
        via_trusted: TrustedRoutine | None = None,
    ) -> Authorization:
        if step.adapter not in self._adapters:
            return Authorization(False, f"Unknown adapter '{step.adapter}'")

        if step.sensitivity in HARD_CONFIRMATION_CLASSES:
            if not hard_confirmed:
                return Authorization(
                    False,
                    f"Hard confirmation required for {step.sensitivity.value} action",
                    requires_hard_confirmation=True,
                )
            if not approved:
                return Authorization(False, "User rejected hard-confirmation step")
            return Authorization(True, "Hard confirmation granted")

        # Trusted routines may run matching non-sensitive steps without a fresh approval.
        if via_trusted is not None and via_trusted.enabled:
            if self._step_in_scopes(step, via_trusted.scopes):
                return Authorization(True, f"Allowed by trusted routine '{via_trusted.name}'")
            return Authorization(False, "Trusted routine scopes do not cover this step")

        if approved:
            return Authorization(True, "User approved step")

        if self._step_in_scopes(step, self._grants) and step.sensitivity == Sensitivity.READ:
            return Authorization(True, "Covered by existing read scope")

        return Authorization(False, "Approval required")

    def execute_plan(
        self,
        plan: Plan,
        decision: ApprovalDecision,
        *,
        dry_run: bool = False,
        hard_confirmed_step_ids: frozenset[str] | None = None,
        use_trusted_match: bool = True,
    ) -> list[StepResult]:
        hard_confirmed_step_ids = hard_confirmed_step_ids or frozenset()
        results: list[StepResult] = []

        trusted = self.find_matching_routine(plan) if use_trusted_match else None
        fingerprint = self.fingerprint_plan(plan)
        if trusted is not None:
            self._audit.record(
                "trusted_routine_matched",
                f"Matched trusted routine '{trusted.name}'",
                routine_id=trusted.id,
                plan_id=plan.id,
                fingerprint=fingerprint,
            )

        for step in plan.steps:
            if trusted is not None and not step.requires_hard_confirmation():
                approved = True
            else:
                approved = step.id in decision.approved_step_ids

            auth = self.authorize_step(
                step,
                approved=approved,
                hard_confirmed=step.id in hard_confirmed_step_ids,
                via_trusted=trusted,
            )
            if not auth.allowed:
                result = StepResult(
                    step_id=step.id,
                    ok=False,
                    output="",
                    error=auth.reason,
                    dry_run=dry_run,
                )
                results.append(result)
                self._audit.record(
                    "step_denied",
                    auth.reason,
                    plan_id=plan.id,
                    step_id=step.id,
                )
                continue

            adapter = self._adapters[step.adapter]
            result = adapter.execute(step.action, step.args, dry_run=dry_run)
            result = StepResult(
                step_id=step.id,
                ok=result.ok,
                output=result.output,
                error=result.error,
                dry_run=dry_run,
            )
            results.append(result)
            self._audit.record(
                "step_executed" if result.ok else "step_failed",
                step.summary,
                plan_id=plan.id,
                step_id=step.id,
                dry_run=dry_run,
                output=result.output[:500],
                error=result.error,
            )

        if decision.promote_to_trusted and decision.trusted_name:
            self._promote(plan, decision.trusted_name, fingerprint)

        return results

    def _promote(self, plan: Plan, name: str, fingerprint: str) -> TrustedRoutine:
        scopes = [
            ScopeGrant(
                id=new_id("scp_"),
                adapter=step.adapter,
                actions=frozenset({step.action}),
            )
            for step in plan.steps
            if step.sensitivity not in HARD_CONFIRMATION_CLASSES
        ]
        # Replace any existing routine with the same fingerprint.
        for existing_id, existing in list(self._routines.items()):
            if existing.plan_fingerprint == fingerprint:
                del self._routines[existing_id]

        routine = TrustedRoutine(
            id=new_id("rtn_"),
            name=name,
            plan_fingerprint=fingerprint,
            scopes=scopes,
            goal_norm=normalize_goal(plan.goal),
        )
        self._routines[routine.id] = routine
        self._audit.record(
            "routine_trusted",
            f"Promoted plan to trusted routine '{name}'",
            routine_id=routine.id,
            fingerprint=fingerprint,
        )
        return routine

    def _step_in_scopes(self, step: ToolStep, scopes: list[ScopeGrant]) -> bool:
        for grant in scopes:
            if grant.adapter != step.adapter:
                continue
            if step.action not in grant.actions:
                continue
            if grant.paths:
                path = str(step.args.get("path", step.args.get("root", "")))
                if path and not any(path.startswith(p) for p in grant.paths):
                    continue
            if grant.apps:
                app = str(step.args.get("app", step.args.get("name", "")))
                if app and app.lower() not in {a.lower() for a in grant.apps}:
                    continue
            if grant.commands:
                command = str(step.args.get("command", ""))
                if command and command not in grant.commands:
                    continue
            return True
        return False
