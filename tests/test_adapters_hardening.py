"""Windows adapter hardening tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from arbora.adapters.desktop import APP_ALIASES, DesktopAdapter
from arbora.adapters.files import FilesAdapter, resolve_user_path, search_files_by_name, user_temp_dir
from arbora.adapters.powershell import ShellOutcome, ps_quote, run_powershell
from arbora.adapters.terminal import TerminalAdapter


def test_ps_quote_escapes_single_quotes():
    assert ps_quote("O'Brien") == "'O''Brien'"


def test_resolve_user_path_expands_home():
    resolved = resolve_user_path("~/ArboraWorkday")
    assert resolved == (Path.home() / "ArboraWorkday").resolve(strict=False)


def test_files_list_permission_error(tmp_path: Path):
    adapter = FilesAdapter()
    target = tmp_path / "locked"
    target.mkdir()
    resolved = target.resolve()

    original = Path.iterdir

    def boom(self: Path):
        if self.resolve() == resolved:
            raise PermissionError("denied")
        return original(self)

    with patch.object(Path, "iterdir", boom):
        result = adapter.execute("list_directory", {"path": str(target)}, dry_run=False)
    assert result.ok is False
    assert "Permission denied" in (result.error or "")


def test_files_write_and_list_roundtrip(tmp_path: Path):
    adapter = FilesAdapter()
    path = tmp_path / "note.txt"
    written = adapter.execute(
        "write_text",
        {"path": str(path), "content": "hello"},
        dry_run=False,
    )
    assert written.ok
    listed = adapter.execute("list_directory", {"path": str(tmp_path)}, dry_run=False)
    assert listed.ok
    assert "note.txt" in listed.output


def test_open_in_explorer_requires_path():
    adapter = FilesAdapter()
    result = adapter.execute("open_in_explorer", {}, dry_run=True)
    assert result.ok is False
    assert "path" in (result.error or "").lower()


def test_open_in_explorer_dry_run(tmp_path: Path):
    adapter = FilesAdapter()
    result = adapter.execute("open_in_explorer", {"path": str(tmp_path)}, dry_run=True)
    assert result.ok
    assert result.dry_run
    assert "Explorer" in result.output


def test_recycle_bin_inspect_dry_run():
    adapter = FilesAdapter()
    result = adapter.execute("inspect_recycle_bin", {}, dry_run=True)
    assert result.ok
    assert result.dry_run


def test_recycle_bin_empty_dry_run():
    adapter = FilesAdapter()
    result = adapter.execute("empty_recycle_bin", {}, dry_run=True)
    assert result.ok
    assert result.dry_run
    assert "empty" in result.output.lower()
    adapter = DesktopAdapter()
    result = adapter.execute("launch_app", {"name": "notepad"}, dry_run=True)
    assert result.ok
    assert "notepad.exe" in result.output
    assert APP_ALIASES["notepad"] == "notepad.exe"


def test_search_by_name_requires_path():
    adapter = FilesAdapter()
    result = adapter.execute("search_by_name", {"pattern": "*.txt"}, dry_run=True)
    assert result.ok is False
    assert "path" in (result.error or "").lower()


def test_search_by_name_dry_run(tmp_path: Path):
    adapter = FilesAdapter()
    result = adapter.execute(
        "search_by_name",
        {"path": str(tmp_path), "pattern": "*.pdf"},
        dry_run=True,
    )
    assert result.ok
    assert result.dry_run
    assert "*.pdf" in result.output


def test_search_files_by_name_matches_nested(tmp_path: Path):
    (tmp_path / "skip.txt").write_text("a", encoding="utf-8")
    nested = tmp_path / "sub"
    nested.mkdir()
    target = nested / "invoice.pdf"
    target.write_text("b", encoding="utf-8")
    hits = search_files_by_name(tmp_path, "invoice", max_depth=2)
    assert target in hits
    shallow = search_files_by_name(tmp_path, "invoice", max_depth=0)
    assert target not in shallow
    listed = FilesAdapter().execute(
        "search_by_name",
        {"path": str(tmp_path), "pattern": "invoice.pdf"},
        dry_run=False,
    )
    assert listed.ok
    assert "invoice.pdf" in listed.output


def test_inspect_user_temp_dry_run(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("TEMP", str(tmp_path))
    adapter = FilesAdapter()
    result = adapter.execute("inspect_user_temp", {}, dry_run=True)
    assert result.ok
    assert result.dry_run
    assert "TEMP" in result.output


def test_clean_user_temp_deletes_files_not_dirs(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("TEMP", str(tmp_path))
    keep_dir = tmp_path / "keepme"
    keep_dir.mkdir()
    doomed = tmp_path / "junk.tmp"
    doomed.write_text("x", encoding="utf-8")
    preview = FilesAdapter().execute("inspect_user_temp", {}, dry_run=False)
    assert preview.ok
    assert "junk.tmp" in preview.output
    dry = FilesAdapter().execute("clean_user_temp", {}, dry_run=True)
    assert dry.ok and dry.dry_run
    assert doomed.exists()
    cleaned = FilesAdapter().execute("clean_user_temp", {}, dry_run=False)
    assert cleaned.ok
    assert not doomed.exists()
    assert keep_dir.exists()
    assert user_temp_dir() == tmp_path.resolve()


def test_desktop_focus_requires_title():
    adapter = DesktopAdapter()
    result = adapter.execute("focus_window", {}, dry_run=True)
    assert result.ok is False
    assert "title_contains" in (result.error or "")


def test_terminal_timeout_surface():
    adapter = TerminalAdapter()
    fake = ShellOutcome(ok=False, stdout="", stderr="", timed_out=True, error="PowerShell timed out after 1s")
    with patch("arbora.adapters.terminal.run_powershell", return_value=fake):
        with patch("arbora.adapters.terminal.require_windows", return_value=None):
            result = adapter.execute(
                "run_powershell",
                {"command": "Start-Sleep -Seconds 30", "timeout_seconds": 1},
                dry_run=False,
            )
    assert result.ok is False
    assert "timed out" in (result.error or "").lower()


def test_run_powershell_truncates(monkeypatch):
    class FakeCompleted:
        returncode = 0
        stdout = "x" * 20_000
        stderr = ""

    def fake_run(*args, **kwargs):
        return FakeCompleted()

    monkeypatch.setattr("arbora.adapters.powershell.subprocess.run", fake_run)
    outcome = run_powershell("Write-Output test", max_output_chars=100)
    assert outcome.ok
    assert "truncated" in outcome.stdout
