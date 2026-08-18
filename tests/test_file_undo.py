"""Tests for file organise apply + undo."""

from __future__ import annotations

from pathlib import Path

from arbora.adapters.files import FilesAdapter, plan_organise_moves
from arbora.cli.session import approve_all, build_runtime
from arbora.preferences.store import set_preference


def test_plan_organise_moves_groups_by_extension(tmp_path: Path):
    root = tmp_path / "Downloads"
    root.mkdir()
    (root / "photo.jpg").write_text("x", encoding="utf-8")
    (root / "notes.txt").write_text("y", encoding="utf-8")
    moves = plan_organise_moves(root)
    buckets = {bucket for bucket, _src, _dst in moves}
    assert buckets == {"images", "documents"}


def test_apply_and_undo_organise_roundtrip(tmp_path: Path):
    journal: list[dict] = []

    def loader() -> list[dict]:
        return list(journal)

    def store(rows: list[dict]) -> None:
        journal.clear()
        journal.extend(rows)

    adapter = FilesAdapter(undo_loader=loader, undo_store=store)
    root = tmp_path / "Downloads"
    root.mkdir()
    (root / "photo.jpg").write_text("x", encoding="utf-8")

    preview = adapter.execute("preview_organise", {"path": str(root)}, dry_run=False)
    assert preview.ok
    assert "images" in preview.output

    applied = adapter.execute("apply_organise", {"path": str(root)}, dry_run=False)
    assert applied.ok
    assert (root / "images" / "photo.jpg").exists()
    assert not (root / "photo.jpg").exists()
    assert journal

    undo = adapter.execute("undo_last_organise", {}, dry_run=False)
    assert undo.ok
    assert (root / "photo.jpg").exists()
    assert not (root / "images" / "photo.jpg").exists()
    assert journal == []


def test_undo_organise_plan_via_runtime(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "Downloads"
    root.mkdir()
    (root / "doc.pdf").write_text("pdf", encoding="utf-8")
    seed = build_runtime(memory_root=tmp_path, provider="echo")
    set_preference(seed.memory, "downloads_folder", str(root))
    runtime = build_runtime(memory_root=tmp_path, provider="echo")

    organise = runtime.planner.plan("organise my downloads")
    runtime.broker.execute_plan(organise, approve_all(organise), dry_run=False)
    assert (root / "documents" / "doc.pdf").exists()

    undo_plan = runtime.planner.plan("undo last organise")
    results = runtime.broker.execute_plan(undo_plan, approve_all(undo_plan), dry_run=False)
    assert all(r.ok for r in results)
    assert (root / "doc.pdf").exists()
