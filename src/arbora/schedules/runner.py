"""Run due trusted-routine schedules through the permission broker."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from arbora.cli.session import Runtime, approve_all
from arbora.core.types import ExecutionReport, TrustedRoutine
from arbora.memory.store import LocalMemoryStore
from arbora.schedules.store import RoutineSchedule, load_schedules, persist_schedules


@dataclass
class RunDueResult:
    schedule_id: str
    routine_id: str
    ok: bool
    skipped: bool
    message: str
    report: ExecutionReport | None = None


def is_due(schedule: RoutineSchedule, now: datetime) -> bool:
    if not schedule.enabled:
        return False
    if schedule.days and now.weekday() not in schedule.days:
        return False
    scheduled_at = now.replace(hour=schedule.hour, minute=schedule.minute, second=0, microsecond=0)
    if now < scheduled_at:
        return False
    if schedule.last_run_date == now.date().isoformat():
        return False
    return True


def _routine_by_id(runtime: Runtime, routine_id: str) -> TrustedRoutine | None:
    for routine in runtime.broker.list_routines():
        if routine.id == routine_id:
            return routine
    return None


def run_schedule(
    runtime: Runtime,
    schedule: RoutineSchedule,
    *,
    dry_run: bool | None = None,
    now: datetime | None = None,
    persist: bool = True,
) -> RunDueResult:
    """Execute one schedule if its trusted routine still matches the planned goal."""
    now = now or datetime.now().astimezone()
    routine = _routine_by_id(runtime, schedule.routine_id)
    if routine is None:
        return RunDueResult(
            schedule_id=schedule.id,
            routine_id=schedule.routine_id,
            ok=False,
            skipped=True,
            message="Trusted routine not found — schedule skipped",
        )
    if not routine.enabled:
        return RunDueResult(
            schedule_id=schedule.id,
            routine_id=schedule.routine_id,
            ok=False,
            skipped=True,
            message=f"Trusted routine '{routine.name}' is disabled — schedule skipped",
        )
    if not routine.goal_norm and not routine.goal_text:
        return RunDueResult(
            schedule_id=schedule.id,
            routine_id=schedule.routine_id,
            ok=False,
            skipped=True,
            message=f"Trusted routine '{routine.name}' has no stored goal — schedule skipped",
        )

    goal = routine.goal_text or routine.goal_norm
    plan = runtime.planner.plan(goal)
    matched = runtime.broker.find_matching_routine(plan)
    if matched is None or matched.id != routine.id:
        return RunDueResult(
            schedule_id=schedule.id,
            routine_id=schedule.routine_id,
            ok=False,
            skipped=True,
            message="Plan no longer matches trusted routine fingerprint — schedule skipped",
        )
    if plan.has_hard_confirmation_steps:
        return RunDueResult(
            schedule_id=schedule.id,
            routine_id=schedule.routine_id,
            ok=False,
            skipped=True,
            message="Plan includes hard-confirmation steps — scheduled runs are not allowed",
        )

    effective_dry_run = schedule.dry_run if dry_run is None else dry_run
    runtime.audit.record(
        "schedule_run_started",
        f"Running scheduled routine '{routine.name}'",
        schedule_id=schedule.id,
        routine_id=routine.id,
        dry_run=effective_dry_run,
    )
    results = runtime.broker.execute_plan(
        plan,
        approve_all(plan),
        dry_run=effective_dry_run,
    )
    report = ExecutionReport(plan_id=plan.id, results=results)
    schedule.last_run_date = now.date().isoformat()
    if persist:
        _persist_schedule(runtime.memory, schedule)

    runtime.audit.record(
        "schedule_run_finished",
        f"Scheduled routine '{routine.name}' finished ok={report.all_ok}",
        schedule_id=schedule.id,
        routine_id=routine.id,
        plan_id=plan.id,
        ok=report.all_ok,
    )
    return RunDueResult(
        schedule_id=schedule.id,
        routine_id=schedule.routine_id,
        ok=report.all_ok,
        skipped=False,
        message="Scheduled run completed",
        report=report,
    )


def run_due_schedules(
    runtime: Runtime,
    *,
    dry_run: bool | None = None,
    now: datetime | None = None,
) -> list[RunDueResult]:
    now = now or datetime.now().astimezone()
    results: list[RunDueResult] = []
    for schedule in load_schedules(runtime.memory):
        if not is_due(schedule, now):
            continue
        results.append(run_schedule(runtime, schedule, dry_run=dry_run, now=now))
    return results


def _persist_schedule(memory: LocalMemoryStore, updated: RoutineSchedule) -> None:
    schedules = load_schedules(memory)
    rows = [
        updated if schedule.id == updated.id else schedule for schedule in schedules
    ]
    persist_schedules(memory, rows)
