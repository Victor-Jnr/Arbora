"""Recent goal history stored in encrypted local memory."""

from __future__ import annotations

from arbora.memory.store import LocalMemoryStore

MEMORY_KEY = "recent_goals"
MAX_GOALS = 20


def record_goal(memory: LocalMemoryStore, goal: str) -> None:
    text = goal.strip()
    if not text or text.startswith("/"):
        return
    rows = load_goals(memory)
    rows = [item for item in rows if item != text]
    rows.append(text)
    memory.set(MEMORY_KEY, rows[-MAX_GOALS:])


def load_goals(memory: LocalMemoryStore) -> list[str]:
    rows = memory.get(MEMORY_KEY)
    if not isinstance(rows, list):
        return []
    return [str(item) for item in rows if str(item).strip()]


def list_recent_goals(memory: LocalMemoryStore, *, limit: int = 10) -> list[str]:
    rows = load_goals(memory)
    if limit <= 0:
        return []
    return list(reversed(rows[-limit:]))
