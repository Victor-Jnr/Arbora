"""Smoke test for Tkinter chat module import and Trust UX helpers."""

from __future__ import annotations

import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path

from apps.desktop_chat.app import (
    ArboraChatApp,
    format_audit_events,
    format_routine_detail,
    format_routine_rows,
    main,
)
from arbora.cli.session import approve_all, build_runtime, persist_routines
from arbora.core.types import AuditEvent, TrustedRoutine


def test_arbora_chat_app_constructs():
    root = tk.Tk()
    root.withdraw()
    try:
        app = ArboraChatApp(root)
        assert app._runtime is not None
        assert app.dry_run_var.get() is True
    finally:
        root.destroy()


def test_main_callable():
    assert callable(main)


def test_format_routine_helpers():
    routine = TrustedRoutine(
        id="rtn_abcdefghijkl",
        name="list-downloads",
        plan_fingerprint="fp123",
        scopes=[],
        version=2,
        goal_norm="list files in ~/downloads",
    )
    assert format_routine_rows([routine]) == ["list-downloads  (rtn_abcd…)"]
    detail = format_routine_detail(routine)
    assert "list-downloads" in detail
    assert "fp123" in detail
    assert "v2" in detail


def test_format_audit_events():
    event = AuditEvent(
        id="aud_1",
        kind="plan_created",
        message="test plan",
        payload={"plan_id": "p1"},
        created_at=datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc),
    )
    body = format_audit_events([event])
    assert "plan_created" in body
    assert "test plan" in body
    assert "plan_id=p1" in body
    assert format_audit_events([]) == "(audit log empty for this session)\n"


def test_trust_ux_dialogs_and_revoke(tmp_path: Path):
    root = tk.Tk()
    root.withdraw()
    try:
        app = ArboraChatApp(root)
        app._runtime = build_runtime(memory_root=tmp_path, provider="echo")
        plan = app._runtime.planner.plan("list files in ~/Downloads")
        decision = approve_all(plan, promote_to_trusted=True, trusted_name="list-downloads")
        app._runtime.broker.execute_plan(plan, decision, dry_run=True)
        persist_routines(app._runtime)
        assert len(app._runtime.broker.list_routines()) == 1

        app._runtime.audit.record("plan_created", "test plan", plan_id="p1")
        app.show_audit()
        audit_dialog = [c for c in root.winfo_children() if isinstance(c, tk.Toplevel)][-1]
        texts = [w for w in _walk(audit_dialog) if isinstance(w, tk.Text)]
        assert texts
        body = texts[0].get("1.0", "end")
        assert "plan_created" in body
        audit_dialog.destroy()

        app.show_routines()
        routines_dialog = [c for c in root.winfo_children() if isinstance(c, tk.Toplevel)][-1]
        listboxes = [w for w in _walk(routines_dialog) if isinstance(w, tk.Listbox)]
        assert listboxes
        assert listboxes[0].size() == 1

        routine = app._runtime.broker.list_routines()[0]
        assert app._runtime.broker.revoke_routine(routine.id)
        persist_routines(app._runtime)
        assert app._runtime.broker.list_routines() == []
        routines_dialog.destroy()
    finally:
        root.destroy()


def _walk(widget):
    yield widget
    for child in widget.winfo_children():
        yield from _walk(child)
