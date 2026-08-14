"""Regression tests for persisted audit events."""

from __future__ import annotations

from pathlib import Path

from arbora.cli.session import build_runtime
from arbora.core.audit_store import MAX_EVENTS, load_audit_events


def test_audit_events_persist_across_runtime(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    runtime.audit.record("plan_created", "first session plan", plan_id="p1")

    runtime2 = build_runtime(memory_root=tmp_path, provider="echo")
    kinds = [event.kind for event in runtime2.audit.events()]
    assert "adapter_registered" in kinds
    assert "plan_created" in kinds
    assert any(event.payload.get("plan_id") == "p1" for event in runtime2.audit.events())


def test_audit_trim_keeps_latest_events(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    for index in range(MAX_EVENTS + 25):
        runtime.audit.record("test_event", f"event-{index}")

    stored = load_audit_events(runtime.memory)
    assert len(stored) == MAX_EVENTS
    assert stored[-1].message == f"event-{MAX_EVENTS + 24}"


def test_memory_wipe_clears_audit(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    runtime.audit.record("plan_created", "to be wiped", plan_id="p2")
    runtime.memory.wipe()

    runtime2 = build_runtime(memory_root=tmp_path, provider="echo")
    assert not any(
        event.kind == "plan_created" and event.payload.get("plan_id") == "p2"
        for event in runtime2.audit.events()
    )
