"""Append-only audit trail for plans, approvals, and tool outcomes."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from arbora.core.types import AuditEvent, new_id, utc_now


class AuditLog:
    """In-memory audit log for the Stage 1 prototype."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def record(self, kind: str, message: str, **payload: Any) -> AuditEvent:
        event = AuditEvent(
            id=new_id("aud_"),
            kind=kind,
            message=message,
            payload=payload,
            created_at=utc_now(),
        )
        self._events.append(event)
        return event

    def events(self) -> list[AuditEvent]:
        return list(self._events)

    def as_dicts(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for event in self._events:
            row = asdict(event)
            row["created_at"] = event.created_at.isoformat()
            rows.append(row)
        return rows
