"""Serialize routine schedules to/from encrypted local memory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from arbora.core.types import new_id
from arbora.memory.store import LocalMemoryStore

MEMORY_KEY = "routine_schedules"

WEEKDAY_ALIASES: dict[str, int] = {
    "mon": 0,
    "monday": 0,
    "tue": 1,
    "tues": 1,
    "tuesday": 1,
    "wed": 2,
    "wednesday": 2,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "thursday": 3,
    "fri": 4,
    "friday": 4,
    "sat": 5,
    "saturday": 5,
    "sun": 6,
    "sunday": 6,
}


@dataclass
class RoutineSchedule:
    """Daily time trigger for a single trusted routine."""

    id: str
    routine_id: str
    hour: int
    minute: int
    days: frozenset[int] = frozenset()
    enabled: bool = True
    dry_run: bool = True
    last_run_date: str | None = None


def parse_time(value: str) -> tuple[int, int]:
    parts = value.strip().split(":", maxsplit=1)
    if len(parts) != 2:
        raise ValueError(f"Invalid time '{value}'. Use HH:MM (24-hour).")
    hour = int(parts[0])
    minute = int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid time '{value}'. Hour must be 0-23 and minute 0-59.")
    return hour, minute


def parse_days(spec: str | None) -> frozenset[int]:
    if not spec or not spec.strip():
        return frozenset()
    days: set[int] = set()
    for token in spec.replace(",", " ").split():
        key = token.strip().lower()
        if key not in WEEKDAY_ALIASES:
            raise ValueError(
                f"Unknown weekday '{token}'. Use mon,tue,wed,thu,fri,sat,sun or leave empty for every day."
            )
        days.add(WEEKDAY_ALIASES[key])
    return frozenset(days)


def format_days(days: frozenset[int]) -> str:
    if not days:
        return "daily"
    names = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
    return ",".join(names[day] for day in sorted(days))


def schedules_to_dicts(schedules: list[RoutineSchedule]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for schedule in schedules:
        rows.append(
            {
                "id": schedule.id,
                "routine_id": schedule.routine_id,
                "hour": schedule.hour,
                "minute": schedule.minute,
                "days": sorted(schedule.days),
                "enabled": schedule.enabled,
                "dry_run": schedule.dry_run,
                "last_run_date": schedule.last_run_date,
            }
        )
    return rows


def schedules_from_dicts(rows: list[dict[str, Any]] | None) -> list[RoutineSchedule]:
    if not rows:
        return []
    schedules: list[RoutineSchedule] = []
    for row in rows:
        day_values = row.get("days") or []
        schedules.append(
            RoutineSchedule(
                id=str(row["id"]),
                routine_id=str(row["routine_id"]),
                hour=int(row["hour"]),
                minute=int(row["minute"]),
                days=frozenset(int(day) for day in day_values),
                enabled=bool(row.get("enabled", True)),
                dry_run=bool(row.get("dry_run", True)),
                last_run_date=row.get("last_run_date"),
            )
        )
    return schedules


def load_schedules(memory: LocalMemoryStore) -> list[RoutineSchedule]:
    rows = memory.get(MEMORY_KEY)
    return schedules_from_dicts(rows if isinstance(rows, list) else None)


def persist_schedules(memory: LocalMemoryStore, schedules: list[RoutineSchedule]) -> None:
    memory.set(MEMORY_KEY, schedules_to_dicts(schedules))


def add_schedule(
    memory: LocalMemoryStore,
    *,
    routine_id: str,
    time_hhmm: str,
    days: str | None = None,
    dry_run: bool = True,
) -> RoutineSchedule:
    hour, minute = parse_time(time_hhmm)
    schedule = RoutineSchedule(
        id=new_id("sch_"),
        routine_id=routine_id,
        hour=hour,
        minute=minute,
        days=parse_days(days),
        dry_run=dry_run,
    )
    schedules = load_schedules(memory)
    schedules.append(schedule)
    persist_schedules(memory, schedules)
    return schedule


def remove_schedule(memory: LocalMemoryStore, schedule_id: str) -> bool:
    schedules = load_schedules(memory)
    kept = [schedule for schedule in schedules if schedule.id != schedule_id]
    if len(kept) == len(schedules):
        return False
    persist_schedules(memory, kept)
    return True


def schedule_rows(
    schedules: list[RoutineSchedule],
    *,
    routine_names: dict[str, str] | None = None,
) -> list[str]:
    names = routine_names or {}
    rows: list[str] = []
    for schedule in schedules:
        routine_name = names.get(schedule.routine_id, schedule.routine_id)
        state = "on" if schedule.enabled else "off"
        mode = "dry-run" if schedule.dry_run else "live"
        last = schedule.last_run_date or "never"
        rows.append(
            f"{schedule.id}  {routine_name}  {schedule.hour:02d}:{schedule.minute:02d}  "
            f"{format_days(schedule.days)}  {state}  {mode}  last={last}"
        )
    return rows
