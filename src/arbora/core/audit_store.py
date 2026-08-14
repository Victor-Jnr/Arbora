"""Persist audit events in encrypted local memory."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from arbora.core.types import AuditEvent, utc_now
from arbora.memory.store import LocalMemoryStore

MEMORY_KEY = "audit_events"
MAX_EVENTS = 500


def events_to_dicts(events: list[AuditEvent]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in events:
        row = asdict(event)
        row["created_at"] = event.created_at.isoformat()
        rows.append(row)
    return rows


def events_from_dicts(rows: list[dict[str, Any]] | None) -> list[AuditEvent]:
    if not rows:
        return []
    events: list[AuditEvent] = []
    for row in rows:
        created_raw = row.get("created_at")
        if isinstance(created_raw, str):
            created_at = datetime.fromisoformat(created_raw)
        else:
            created_at = utc_now()
        events.append(
            AuditEvent(
                id=str(row.get("id", "")),
                kind=str(row.get("kind", "")),
                message=str(row.get("message", "")),
                payload=dict(row.get("payload") or {}),
                created_at=created_at,
            )
        )
    return events


def load_audit_events(memory: LocalMemoryStore) -> list[AuditEvent]:
    rows = memory.get(MEMORY_KEY)
    return events_from_dicts(rows if isinstance(rows, list) else None)


def persist_audit_events(memory: LocalMemoryStore, events: list[AuditEvent]) -> None:
    trimmed = events[-MAX_EVENTS:]
    memory.set(MEMORY_KEY, events_to_dicts(trimmed))
