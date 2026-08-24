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


def test_copy_file_preview_and_copy(tmp_path: Path):
    adapter = FilesAdapter()
    source = tmp_path / "report.pdf"
    dest_dir = tmp_path / "Documents"
    dest_dir.mkdir()
    source.write_text("pdf", encoding="utf-8")
    dest = dest_dir / "report.pdf"
    dry = adapter.execute(
        "copy_file",
        {"source": str(source), "destination": str(dest_dir)},
        dry_run=True,
    )
    assert dry.ok and dry.dry_run
    assert source.exists() and not dest.exists()
    preview = adapter.execute(
        "preview_copy_move",
        {"source": str(source), "destination": str(dest_dir), "operation": "copy"},
        dry_run=False,
    )
    assert preview.ok
    assert "report.pdf" in preview.output
    copied = adapter.execute(
        "copy_file",
        {"source": str(source), "destination": str(dest_dir)},
        dry_run=False,
    )
    assert copied.ok
    assert source.exists()
    assert dest.read_text(encoding="utf-8") == "pdf"
    refused = adapter.execute(
        "copy_file",
        {"source": str(source), "destination": str(dest_dir)},
        dry_run=False,
    )
    assert refused.ok is False
    assert "already exists" in (refused.error or "").lower()


def test_move_file_records_undo(tmp_path: Path):
    journal: list[dict] = []

    def loader() -> list[dict]:
        return list(journal)

    def store(rows: list[dict]) -> None:
        journal.clear()
        journal.extend(rows)

    adapter = FilesAdapter(undo_loader=loader, undo_store=store)
    source = tmp_path / "invoice.pdf"
    dest_dir = tmp_path / "Documents"
    dest_dir.mkdir()
    source.write_text("inv", encoding="utf-8")
    moved = adapter.execute(
        "move_file",
        {"source": str(source), "destination": str(dest_dir)},
        dry_run=False,
    )
    assert moved.ok
    assert not source.exists()
    assert (dest_dir / "invoice.pdf").exists()
    assert journal
    undo = adapter.execute("undo_last_organise", {}, dry_run=False)
    assert undo.ok
    assert source.exists()
    assert not (dest_dir / "invoice.pdf").exists()


def test_copy_move_requires_paths():
    adapter = FilesAdapter()
    result = adapter.execute("copy_file", {}, dry_run=True)
    assert result.ok is False
    assert "source" in (result.error or "").lower()
