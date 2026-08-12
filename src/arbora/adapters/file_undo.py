"""Undo journal for reversible file organise moves."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass(frozen=True)
class FileMoveRecord:
    source: str
    destination: str

    def to_dict(self) -> dict[str, str]:
        return {"source": self.source, "destination": self.destination}

    @staticmethod
    def from_dict(row: dict[str, Any]) -> FileMoveRecord:
        return FileMoveRecord(
            source=str(row.get("source", "")),
            destination=str(row.get("destination", "")),
        )


@dataclass(frozen=True)
class UndoBatch:
    batch_id: str
    root: str
    moves: tuple[FileMoveRecord, ...]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "root": self.root,
            "moves": [move.to_dict() for move in self.moves],
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(row: dict[str, Any]) -> UndoBatch:
        moves = tuple(FileMoveRecord.from_dict(item) for item in row.get("moves") or [])
        return UndoBatch(
            batch_id=str(row.get("batch_id", "")),
            root=str(row.get("root", "")),
            moves=moves,
            created_at=str(row.get("created_at", "")),
        )


UndoJournalStore = Callable[[list[dict[str, Any]]], None]
UndoJournalLoader = Callable[[], list[dict[str, Any]]]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_batches(loader: UndoJournalLoader | None) -> list[UndoBatch]:
    if loader is None:
        return []
    rows = loader()
    batches: list[UndoBatch] = []
    for row in rows:
        try:
            batches.append(UndoBatch.from_dict(row))
        except (TypeError, ValueError):
            continue
    return batches


def save_batches(store: UndoJournalStore | None, batches: list[UndoBatch], *, limit: int = 20) -> None:
    if store is None:
        return
    trimmed = batches[-limit:]
    store([batch.to_dict() for batch in trimmed])


def append_batch(
    loader: UndoJournalLoader | None,
    store: UndoJournalStore | None,
    batch: UndoBatch,
) -> None:
    batches = load_batches(loader)
    batches.append(batch)
    save_batches(store, batches)


def pop_last_batch(
    loader: UndoJournalLoader | None,
    store: UndoJournalStore | None,
) -> UndoBatch | None:
    batches = load_batches(loader)
    if not batches:
        return None
    last = batches.pop()
    save_batches(store, batches)
    return last
