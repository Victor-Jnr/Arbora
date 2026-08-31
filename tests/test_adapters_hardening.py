"""Windows adapter hardening tests."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from arbora.adapters.desktop import (
    APP_ALIASES,
    CLIPBOARD_SAVE_MAX_CHARS,
    DesktopAdapter,
    clipboard_looks_secret,
    clipboard_save_payload,
    close_window_script,
    format_battery_report,
    format_clipboard_report,
    format_default_browser_report,
    format_display_report,
    format_printer_report,
    format_startup_report,
    format_windows_update_report,
    installed_browser_alias,
    is_safe_http_url,
    open_in_browser_script,
    parse_battery_snapshot,
    parse_clipboard_snapshot,
    parse_default_browser_snapshot,
    parse_display_snapshot,
    parse_printer_snapshot,
    parse_startup_snapshot,
    parse_windows_update_snapshot,
    browser_name_from_progid,
    resolve_launch_target,
)
from arbora.adapters.files import (
    FilesAdapter,
    is_protected_delete_root,
    list_old_files,
    list_recent_files,
    resolve_user_path,
    search_files_by_name,
    user_temp_dir,
)
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


def test_resolve_launch_target_chrome_alias():
    target = resolve_launch_target("chrome")
    assert target.lower().endswith("chrome.exe")
    assert APP_ALIASES["google chrome"] == "chrome.exe"
    assert APP_ALIASES["vscode"] == "Code.exe"
    dry = DesktopAdapter().execute("launch_app", {"name": "chrome"}, dry_run=True)
    assert dry.ok and dry.dry_run
    assert "chrome" in dry.output.lower()


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


def test_list_recent_requires_path():
    adapter = FilesAdapter()
    result = adapter.execute("list_recent", {}, dry_run=True)
    assert result.ok is False
    assert "path" in (result.error or "").lower()


def test_list_recent_dry_run(tmp_path: Path):
    adapter = FilesAdapter()
    result = adapter.execute("list_recent", {"path": str(tmp_path)}, dry_run=True)
    assert result.ok
    assert result.dry_run
    assert "newest" in result.output.lower()


def test_list_recent_files_orders_by_mtime(tmp_path: Path):
    older = tmp_path / "older.txt"
    newer = tmp_path / "newer.txt"
    nested = tmp_path / "sub"
    nested.mkdir()
    nested_file = nested / "nested.txt"
    older.write_text("a", encoding="utf-8")
    newer.write_text("b", encoding="utf-8")
    nested_file.write_text("c", encoding="utf-8")
    os.utime(older, (1_000_000, 1_000_000))
    os.utime(nested_file, (2_000_000, 2_000_000))
    os.utime(newer, (3_000_000, 3_000_000))
    rows = list_recent_files(tmp_path, max_depth=2, max_results=10)
    names = [item.name for item, _mtime, _size in rows]
    assert names[0] == "newer.txt"
    assert "nested.txt" in names
    shallow = list_recent_files(tmp_path, max_depth=0, max_results=10)
    shallow_names = [item.name for item, _mtime, _size in shallow]
    assert "nested.txt" not in shallow_names
    listed = FilesAdapter().execute("list_recent", {"path": str(tmp_path)}, dry_run=False)
    assert listed.ok
    assert "newer.txt" in listed.output
    assert listed.output.index("newer.txt") < listed.output.index("older.txt")


def test_inspect_old_files_requires_path():
    result = FilesAdapter().execute("inspect_old_files", {}, dry_run=True)
    assert result.ok is False
    assert "path" in (result.error or "").lower()


def test_inspect_old_files_dry_run(tmp_path: Path):
    result = FilesAdapter().execute(
        "inspect_old_files",
        {"path": str(tmp_path), "older_than_days": 30},
        dry_run=True,
    )
    assert result.ok and result.dry_run
    assert "30" in result.output


def test_list_old_files_top_level_only(tmp_path: Path):
    keep = tmp_path / "fresh.txt"
    doomed = tmp_path / "stale.txt"
    nested_dir = tmp_path / "bucket"
    nested_dir.mkdir()
    nested = nested_dir / "old-nested.txt"
    keep.write_text("new", encoding="utf-8")
    doomed.write_text("old", encoding="utf-8")
    nested.write_text("nested", encoding="utf-8")
    os.utime(doomed, (1_000_000, 1_000_000))
    os.utime(nested, (1_000_000, 1_000_000))
    rows = list_old_files(tmp_path, older_than_days=30, max_results=50)
    names = [item.name for item, _mtime, _size in rows]
    assert names == ["stale.txt"]
    listed = FilesAdapter().execute(
        "inspect_old_files",
        {"path": str(tmp_path), "older_than_days": 30},
        dry_run=False,
    )
    assert listed.ok
    assert "stale.txt" in listed.output
    assert "fresh.txt" not in listed.output
    assert "old-nested.txt" not in listed.output


def test_delete_old_files_dry_run_and_apply(tmp_path: Path):
    keep = tmp_path / "fresh.txt"
    doomed = tmp_path / "stale.txt"
    keep.write_text("new", encoding="utf-8")
    doomed.write_text("old", encoding="utf-8")
    os.utime(doomed, (1_000_000, 1_000_000))
    dry = FilesAdapter().execute(
        "delete_old_files",
        {"path": str(tmp_path), "older_than_days": 30},
        dry_run=True,
    )
    assert dry.ok and dry.dry_run
    assert doomed.exists()
    deleted = FilesAdapter().execute(
        "delete_old_files",
        {"path": str(tmp_path), "older_than_days": 30},
        dry_run=False,
    )
    assert deleted.ok
    assert not doomed.exists()
    assert keep.exists()


def test_delete_old_files_refuses_drive_root():
    assert is_protected_delete_root(Path("C:\\"))
    result = FilesAdapter().execute(
        "delete_old_files",
        {"path": "C:\\", "older_than_days": 30},
        dry_run=True,
    )
    assert result.ok is False
    assert "protected" in (result.error or "").lower()


def test_copy_file_dry_run_and_missing_source(tmp_path: Path):
    adapter = FilesAdapter()
    missing = adapter.execute("preview_copy_move", {}, dry_run=True)
    assert missing.ok is False
    source = tmp_path / "note.txt"
    source.write_text("hi", encoding="utf-8")
    dry = adapter.execute(
        "copy_file",
        {"source": str(source), "destination": str(tmp_path / "out.txt")},
        dry_run=True,
    )
    assert dry.ok and dry.dry_run
    assert not (tmp_path / "out.txt").exists()


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


def test_clipboard_looks_secret_markers():
    assert clipboard_looks_secret("password=hunter2") is True
    assert clipboard_looks_secret("ghp_abcdefghijklmnopqrstuvwxyz012345") is True
    assert clipboard_looks_secret("sk-abcdefghijklmnopqrstuvwxyz") is True
    assert clipboard_looks_secret("meeting notes for Tuesday") is False


def test_inspect_clipboard_dry_run():
    adapter = DesktopAdapter()
    withheld = adapter.execute("inspect_clipboard", {}, dry_run=True)
    assert withheld.ok and withheld.dry_run
    assert "withheld" in withheld.output.lower()
    preview = adapter.execute("inspect_clipboard", {"reveal": True}, dry_run=True)
    assert preview.ok and preview.dry_run
    assert "preview" in preview.output.lower()


def test_inspect_clipboard_withholds_secret_even_when_revealed():
    snapshot = parse_clipboard_snapshot("KIND=text\nLENGTH=16\nTEXT_BEGIN\npassword=hunter2")
    report = format_clipboard_report(snapshot, reveal=True)
    assert "password=hunter2" not in report
    assert "secret" in report.lower()


def test_inspect_clipboard_preview_when_safe():
    snapshot = parse_clipboard_snapshot("KIND=text\nLENGTH=12\nTEXT_BEGIN\nhello world!")
    report = format_clipboard_report(snapshot, reveal=True)
    assert "hello world!" in report
    meta = format_clipboard_report(snapshot, reveal=False)
    assert "hello world!" not in meta
    assert "12" in meta


def test_inspect_clipboard_mocked_powershell():
    fake = ShellOutcome(ok=True, stdout="KIND=empty\nLENGTH=0", stderr="")
    with patch("arbora.adapters.desktop.require_windows", return_value=None), patch(
        "arbora.adapters.desktop.run_powershell", return_value=fake
    ):
        result = DesktopAdapter().execute("inspect_clipboard", {}, dry_run=False)
    assert result.ok
    assert "empty" in result.output.lower()


def test_clipboard_save_payload_refuses_secrets_and_non_text():
    text, error = clipboard_save_payload({"kind": "text", "text": "meeting notes"})
    assert text == "meeting notes"
    assert error == ""
    secret, secret_error = clipboard_save_payload({"kind": "text", "text": "password=hunter2"})
    assert secret is None
    assert "secret" in secret_error.lower()
    empty, empty_error = clipboard_save_payload({"kind": "empty"})
    assert empty is None
    assert "empty" in empty_error.lower()
    image, image_error = clipboard_save_payload({"kind": "image"})
    assert image is None
    assert "image" in image_error.lower()
    too_long, long_error = clipboard_save_payload(
        {"kind": "text", "text": "n" * (CLIPBOARD_SAVE_MAX_CHARS + 1)}
    )
    assert too_long is None
    assert str(CLIPBOARD_SAVE_MAX_CHARS) in long_error


def test_save_clipboard_text_requires_path():
    result = DesktopAdapter().execute("save_clipboard_text", {}, dry_run=True)
    assert result.ok is False
    assert "path" in (result.error or "").lower()


def test_save_clipboard_text_dry_run(tmp_path: Path):
    target = tmp_path / "clip.txt"
    result = DesktopAdapter().execute("save_clipboard_text", {"path": str(target)}, dry_run=True)
    assert result.ok and result.dry_run
    assert not target.exists()
    assert "secret" in result.output.lower() or "unless" in result.output.lower()


def test_save_clipboard_text_mocked_write(tmp_path: Path):
    target = tmp_path / "notes" / "clip.txt"
    fake = ShellOutcome(ok=True, stdout="KIND=text\nLENGTH=11\nTEXT_BEGIN\nhello notes", stderr="")
    with patch("arbora.adapters.desktop.require_windows", return_value=None), patch(
        "arbora.adapters.desktop.run_powershell", return_value=fake
    ):
        result = DesktopAdapter().execute("save_clipboard_text", {"path": str(target)}, dry_run=False)
    assert result.ok
    assert target.read_text(encoding="utf-8") == "hello notes"


def test_save_clipboard_text_mocked_secret_does_not_write(tmp_path: Path):
    target = tmp_path / "clip.txt"
    fake = ShellOutcome(ok=True, stdout="KIND=text\nLENGTH=16\nTEXT_BEGIN\npassword=hunter2", stderr="")
    with patch("arbora.adapters.desktop.require_windows", return_value=None), patch(
        "arbora.adapters.desktop.run_powershell", return_value=fake
    ):
        result = DesktopAdapter().execute("save_clipboard_text", {"path": str(target)}, dry_run=False)
    assert result.ok is False
    assert "secret" in (result.error or "").lower()
    assert not target.exists()


def test_speak_text_requires_text():
    result = DesktopAdapter().execute("speak_text", {}, dry_run=True)
    assert result.ok is False
    assert "text" in (result.error or "").lower()


def test_speak_text_dry_run():
    result = DesktopAdapter().execute("speak_text", {"text": "Please review the plan."}, dry_run=True)
    assert result.ok and result.dry_run
    assert "Please review the plan." in result.output


def test_capture_screenshot_requires_path():
    result = DesktopAdapter().execute("capture_screenshot", {}, dry_run=True)
    assert result.ok is False
    assert "path" in (result.error or "").lower()


def test_capture_screenshot_dry_run(tmp_path: Path):
    target = tmp_path / "shot.png"
    screen = DesktopAdapter().execute("capture_screenshot", {"path": str(target)}, dry_run=True)
    assert screen.ok and screen.dry_run
    assert not target.exists()
    windowed = DesktopAdapter().execute(
        "capture_screenshot",
        {"path": str(target), "window_title": "Notepad"},
        dry_run=True,
    )
    assert windowed.ok and windowed.dry_run
    assert "Notepad" in windowed.output


def test_inspect_network_dry_run_and_no_secrets():
    dry = DesktopAdapter().execute("inspect_network", {}, dry_run=True)
    assert dry.ok and dry.dry_run
    assert "key" in dry.output.lower() or "password" in dry.output.lower()
    fake = ShellOutcome(ok=True, stdout="=== Adapters ===\nEthernet Up", stderr="")
    with patch("arbora.adapters.desktop.require_windows", return_value=None), patch(
        "arbora.adapters.desktop.run_powershell", return_value=fake
    ) as mocked:
        result = DesktopAdapter().execute("inspect_network", {}, dry_run=False)
    assert result.ok
    command = str(mocked.call_args[0][0]).lower()
    assert "key=clear" not in command
    assert "show profile" not in command
    assert "password" not in command


def test_inspect_network_withholds_key_like_output():
    fake = ShellOutcome(ok=True, stdout="Key Content : hunter2", stderr="")
    with patch("arbora.adapters.desktop.require_windows", return_value=None), patch(
        "arbora.adapters.desktop.run_powershell", return_value=fake
    ):
        result = DesktopAdapter().execute("inspect_network", {}, dry_run=False)
    assert result.ok is False
    assert "key" in (result.error or "").lower()


def test_inspect_battery_dry_run():
    result = DesktopAdapter().execute("inspect_battery", {}, dry_run=True)
    assert result.ok and result.dry_run
    assert "battery" in result.output.lower()
    assert "powercfg" in result.output.lower() or "serial" in result.output.lower()


def test_format_battery_report_ac_only_and_charging():
    empty = parse_battery_snapshot("PCSystemType=1\nCOUNT=0")
    report = format_battery_report(empty)
    assert "desktop" in report.lower()
    assert "no battery" in report.lower()
    charged = parse_battery_snapshot(
        "PCSystemType=2\nCOUNT=1\nBATTERY_BEGIN\nNAME=SimBattery\nSTATUS=6\nPERCENT=84\nRUNTIME_MIN=95"
    )
    live = format_battery_report(charged)
    assert "84%" in live
    assert "Charging" in live
    assert "SimBattery" in live
    assert "95 min" in live
    sentinel = parse_battery_snapshot(
        "PCSystemType=2\nCOUNT=1\nBATTERY_BEGIN\nNAME=SimBattery\nSTATUS=3\nPERCENT=100\nRUNTIME_MIN=71582788"
    )
    full = format_battery_report(sentinel)
    assert "71582788" not in full


def test_inspect_battery_mocked_powershell():
    fake = ShellOutcome(ok=True, stdout="PCSystemType=1\nCOUNT=0", stderr="")
    with patch("arbora.adapters.desktop.require_windows", return_value=None), patch(
        "arbora.adapters.desktop.run_powershell", return_value=fake
    ):
        result = DesktopAdapter().execute("inspect_battery", {}, dry_run=False)
    assert result.ok
    assert "no battery" in result.output.lower()


def test_inspect_battery_withholds_secret_like_output():
    fake = ShellOutcome(ok=True, stdout="password=hunter2", stderr="")
    with patch("arbora.adapters.desktop.require_windows", return_value=None), patch(
        "arbora.adapters.desktop.run_powershell", return_value=fake
    ):
        result = DesktopAdapter().execute("inspect_battery", {}, dry_run=False)
    assert result.ok is False
    assert "secret" in (result.error or "").lower()


def test_close_window_requires_title():
    result = DesktopAdapter().execute("close_window", {}, dry_run=True)
    assert result.ok is False
    assert "title" in (result.error or "").lower() or "name" in (result.error or "").lower()


def test_close_window_dry_run_is_not_kill():
    result = DesktopAdapter().execute("close_window", {"title_contains": "Notepad"}, dry_run=True)
    assert result.ok and result.dry_run
    assert "WM_CLOSE" in result.output or "close" in result.output.lower()
    assert "force-kill" in result.output.lower() or "closemainwindow" in result.output.lower()
    script = close_window_script("Notepad").lower()
    assert "closemainwindow" in script
    assert "taskkill" not in script
    assert "stop-process" not in script
    assert ".kill(" not in script


def test_close_window_mocked_powershell():
    fake = ShellOutcome(ok=True, stdout="Sent WM_CLOSE to notepad (pid 1) title=Untitled - Notepad", stderr="")
    with patch("arbora.adapters.desktop.require_windows", return_value=None), patch(
        "arbora.adapters.desktop.run_powershell", return_value=fake
    ) as mocked:
        result = DesktopAdapter().execute("close_window", {"title_contains": "Notepad"}, dry_run=False)
    assert result.ok
    command = str(mocked.call_args[0][0]).lower()
    assert "closemainwindow" in command
    assert "taskkill" not in command
    assert "stop-process" not in command


def test_open_in_browser_requires_url_and_browser():
    missing_url = DesktopAdapter().execute("open_in_browser", {"name": "chrome"}, dry_run=True)
    assert missing_url.ok is False
    assert "url" in (missing_url.error or "").lower()
    missing_name = DesktopAdapter().execute(
        "open_in_browser", {"url": "https://example.com"}, dry_run=True
    )
    assert missing_name.ok is False
    assert "chrome" in (missing_name.error or "").lower() or "name" in (missing_name.error or "").lower()
    notepad = DesktopAdapter().execute(
        "open_in_browser",
        {"url": "https://example.com", "name": "notepad"},
        dry_run=True,
    )
    assert notepad.ok is False


def test_is_safe_http_url_rejects_non_http_and_credentials():
    assert is_safe_http_url("https://example.com/path")
    assert is_safe_http_url("http://example.com")
    assert not is_safe_http_url("file:///C:/secrets.txt")
    assert not is_safe_http_url("javascript:alert(1)")
    assert not is_safe_http_url("ftp://files.example")
    assert not is_safe_http_url("https://user:pass@example.com")
    assert not is_safe_http_url("")
    assert installed_browser_alias("Google Chrome") == "chrome"
    assert installed_browser_alias("msedge") == "edge"
    assert installed_browser_alias("notepad") is None


def test_open_in_browser_dry_run_and_rejects_bad_url():
    dry = DesktopAdapter().execute(
        "open_in_browser",
        {"url": "https://example.com", "name": "chrome"},
        dry_run=True,
    )
    assert dry.ok and dry.dry_run
    assert "example.com" in dry.output
    assert "playwright" in dry.output.lower()
    bad = DesktopAdapter().execute(
        "open_in_browser",
        {"url": "file:///C:/tmp", "name": "edge"},
        dry_run=True,
    )
    assert bad.ok is False
    script = open_in_browser_script(r"C:\Program Files\Google\Chrome\Application\chrome.exe", "https://example.com")
    lowered = script.lower()
    assert "start-process" in lowered
    assert "playwright" not in lowered


def test_open_in_browser_mocked_powershell():
    fake = ShellOutcome(ok=True, stdout="Opened https://example.com in chrome.exe", stderr="")
    with patch("arbora.adapters.desktop.require_windows", return_value=None), patch(
        "arbora.adapters.desktop.run_powershell", return_value=fake
    ) as mocked:
        result = DesktopAdapter().execute(
            "open_in_browser",
            {"url": "https://example.com", "name": "chrome"},
            dry_run=False,
        )
    assert result.ok
    command = str(mocked.call_args[0][0]).lower()
    assert "start-process" in command
    assert "https://example.com" in command
    assert "playwright" not in command


def test_inspect_printers_dry_run():
    result = DesktopAdapter().execute("inspect_printers", {}, dry_run=True)
    assert result.ok and result.dry_run
    assert "printer" in result.output.lower()
    assert "job" in result.output.lower() or "secret" in result.output.lower()


def test_format_printer_report_empty_and_default():
    empty = parse_printer_snapshot("COUNT=0")
    report = format_printer_report(empty)
    assert "no printers" in report.lower()
    listed = parse_printer_snapshot(
        "COUNT=2\n"
        "PRINTER_BEGIN\nNAME=OfficeJet\nDEFAULT=True\nSTATUS=3\nWORKOFFLINE=False\n"
        "PORT=USB001\nNETWORK=False\nSHARED=False\n"
        "PRINTER_BEGIN\nNAME=PDF\nDEFAULT=False\nSTATUS=7\nWORKOFFLINE=True\n"
        "PORT=PORTPROMPT:\nNETWORK=False\nSHARED=False\n"
    )
    live = format_printer_report(listed)
    assert "OfficeJet" in live
    assert "default" in live.lower()
    assert "Idle" in live
    assert "PDF" in live
    assert "Offline" in live
    assert "USB001" in live


def test_inspect_printers_mocked_powershell():
    fake = ShellOutcome(ok=True, stdout="COUNT=0", stderr="")
    with patch("arbora.adapters.desktop.require_windows", return_value=None), patch(
        "arbora.adapters.desktop.run_powershell", return_value=fake
    ) as mocked:
        result = DesktopAdapter().execute("inspect_printers", {}, dry_run=False)
    assert result.ok
    assert "no printers" in result.output.lower()
    command = str(mocked.call_args[0][0]).lower()
    assert "win32_printer" in command
    assert "get-printjob" not in command
    assert "password" not in command


def test_inspect_printers_withholds_secret_like_output():
    fake = ShellOutcome(ok=True, stdout="password=hunter2", stderr="")
    with patch("arbora.adapters.desktop.require_windows", return_value=None), patch(
        "arbora.adapters.desktop.run_powershell", return_value=fake
    ):
        result = DesktopAdapter().execute("inspect_printers", {}, dry_run=False)
    assert result.ok is False
    assert "secret" in (result.error or "").lower()


def test_inspect_startup_dry_run():
    result = DesktopAdapter().execute("inspect_startup", {}, dry_run=True)
    assert result.ok and result.dry_run
    assert "startup" in result.output.lower()
    assert "enable" in result.output.lower() or "scheduler" in result.output.lower()


def test_format_startup_report_empty_and_items():
    empty = parse_startup_snapshot("")
    report = format_startup_report(empty)
    assert "no startup" in report.lower()
    listed = parse_startup_snapshot(
        "ITEM_BEGIN\nSOURCE=hkcu_run\nNAME=OneDrive\nCOMMAND=C:\\Apps\\OneDrive.exe /background\n"
        "ITEM_BEGIN\nSOURCE=startup_folder\nNAME=Notes.lnk\nCOMMAND=\n"
        "ITEM_BEGIN\nSOURCE=hkcu_run\nNAME=SecretApp\nCOMMAND=app.exe password=hunter2\n"
    )
    live = format_startup_report(listed)
    assert "OneDrive" in live
    assert "HKCU Run" in live
    assert "Notes.lnk" in live
    assert "Startup folder" in live
    assert "password=hunter2" not in live.lower()
    assert "withheld" in live.lower()


def test_inspect_startup_mocked_powershell():
    fake = ShellOutcome(ok=True, stdout="", stderr="")
    with patch("arbora.adapters.desktop.require_windows", return_value=None), patch(
        "arbora.adapters.desktop.run_powershell", return_value=fake
    ) as mocked:
        result = DesktopAdapter().execute("inspect_startup", {}, dry_run=False)
    assert result.ok
    assert "no startup" in result.output.lower()
    command = str(mocked.call_args[0][0]).lower()
    assert "currentversion\\run" in command or "currentversion\\\\run" in command
    assert "set-itemproperty" not in command
    assert "remove-itemproperty" not in command
    assert "disable" not in command
    assert "schtasks" not in command
    assert "get-scheduledtask" not in command


def test_inspect_startup_withholds_secret_like_output():
    fake = ShellOutcome(ok=True, stdout="password=hunter2", stderr="")
    with patch("arbora.adapters.desktop.require_windows", return_value=None), patch(
        "arbora.adapters.desktop.run_powershell", return_value=fake
    ):
        result = DesktopAdapter().execute("inspect_startup", {}, dry_run=False)
    assert result.ok is False
    assert "secret" in (result.error or "").lower()


def test_inspect_default_browser_dry_run():
    result = DesktopAdapter().execute("inspect_default_browser", {}, dry_run=True)
    assert result.ok and result.dry_run
    assert "browser" in result.output.lower()
    assert "hash" in result.output.lower() or "association" in result.output.lower()


def test_format_default_browser_report_empty_and_progids():
    empty = parse_default_browser_snapshot("")
    report = format_default_browser_report(empty)
    assert "no default browser" in report.lower()
    assert browser_name_from_progid("ChromeHTML") == "Google Chrome"
    assert browser_name_from_progid("MSEdgeHTM") == "Microsoft Edge"
    assert browser_name_from_progid("FirefoxURL-E7CF176E110C211B") == "Mozilla Firefox"
    listed = parse_default_browser_snapshot(
        "HTTPS_PROGID=ChromeHTML\nHTTP_PROGID=ChromeHTML\nHash=should-not-appear\n"
    )
    live = format_default_browser_report(listed)
    assert "Google Chrome" in live
    assert "ChromeHTML" in live
    assert "Hash" not in live
    split = parse_default_browser_snapshot("HTTPS_PROGID=MSEdgeHTM\nHTTP_PROGID=ChromeHTML\n")
    split_report = format_default_browser_report(split)
    assert "Microsoft Edge" in split_report
    assert "HTTP association" in split_report
    assert "Google Chrome" in split_report


def test_inspect_default_browser_mocked_powershell():
    fake = ShellOutcome(ok=True, stdout="", stderr="")
    with patch("arbora.adapters.desktop.require_windows", return_value=None), patch(
        "arbora.adapters.desktop.run_powershell", return_value=fake
    ) as mocked:
        result = DesktopAdapter().execute("inspect_default_browser", {}, dry_run=False)
    assert result.ok
    assert "no default browser" in result.output.lower()
    command = str(mocked.call_args[0][0]).lower()
    assert "userchoice" in command
    assert "progid" in command
    assert "set-itemproperty" not in command
    assert "new-item" not in command
    assert "hash" not in command


def test_inspect_default_browser_withholds_secret_like_output():
    fake = ShellOutcome(ok=True, stdout="password=hunter2", stderr="")
    with patch("arbora.adapters.desktop.require_windows", return_value=None), patch(
        "arbora.adapters.desktop.run_powershell", return_value=fake
    ):
        result = DesktopAdapter().execute("inspect_default_browser", {}, dry_run=False)
    assert result.ok is False
    assert "secret" in (result.error or "").lower()


def test_inspect_display_dry_run():
    result = DesktopAdapter().execute("inspect_display", {}, dry_run=True)
    assert result.ok and result.dry_run
    assert "display" in result.output.lower() or "resolution" in result.output.lower()
    assert "mode" in result.output.lower() or "dpi" in result.output.lower()


def test_format_display_report_empty_and_screens():
    empty = parse_display_snapshot("")
    report = format_display_report(empty)
    assert "no display" in report.lower()
    listed = parse_display_snapshot(
        "COUNT=2\n"
        "DISPLAY_BEGIN\nDEVICE=\\\\.\\DISPLAY1\nPRIMARY=True\n"
        "WIDTH=1920\nHEIGHT=1080\nX=0\nY=0\n"
        "WORKING_WIDTH=1920\nWORKING_HEIGHT=1040\nBITS=32\n"
        "DISPLAY_BEGIN\nDEVICE=\\\\.\\DISPLAY2\nPRIMARY=False\n"
        "WIDTH=2560\nHEIGHT=1440\nX=1920\nY=0\n"
        "WORKING_WIDTH=2560\nWORKING_HEIGHT=1400\nBITS=32\n"
    )
    live = format_display_report(listed)
    assert "Display count: 2" in live
    assert "1920x1080" in live
    assert "2560x1440" in live
    assert "primary" in live.lower()
    assert "working=1920x1040" in live


def test_inspect_display_mocked_powershell():
    fake = ShellOutcome(ok=True, stdout="", stderr="")
    with patch("arbora.adapters.desktop.require_windows", return_value=None), patch(
        "arbora.adapters.desktop.run_powershell", return_value=fake
    ) as mocked:
        result = DesktopAdapter().execute("inspect_display", {}, dry_run=False)
    assert result.ok
    assert "no display" in result.output.lower()
    command = str(mocked.call_args[0][0]).lower()
    assert "allscreens" in command or "screen" in command
    assert "changedisplaysettings" not in command
    assert "setdisplayconfig" not in command
    assert "cds_updateregistry" not in command


def test_inspect_display_withholds_secret_like_output():
    fake = ShellOutcome(ok=True, stdout="password=hunter2", stderr="")
    with patch("arbora.adapters.desktop.require_windows", return_value=None), patch(
        "arbora.adapters.desktop.run_powershell", return_value=fake
    ):
        result = DesktopAdapter().execute("inspect_display", {}, dry_run=False)
    assert result.ok is False
    assert "secret" in (result.error or "").lower()


def test_inspect_windows_update_dry_run():
    result = DesktopAdapter().execute("inspect_windows_update", {}, dry_run=True)
    assert result.ok and result.dry_run
    assert "hotfix" in result.output.lower() or "update" in result.output.lower()
    assert "install" in result.output.lower() or "scan" in result.output.lower()


def test_format_windows_update_report_empty_and_latest():
    empty = parse_windows_update_snapshot("")
    report = format_windows_update_report(empty)
    assert "no windows update" in report.lower()
    listed = parse_windows_update_snapshot(
        "COUNT=12\nUPDATE_BEGIN\nKB=KB5063878\nINSTALLED=2026-08-12\nDESC=Security Update\n"
    )
    live = format_windows_update_report(listed)
    assert "2026-08-12" in live
    assert "KB5063878" in live
    assert "Security Update" in live
    assert "12" in live
    assert "listing withheld" in live.lower()


def test_inspect_windows_update_mocked_powershell():
    fake = ShellOutcome(ok=True, stdout="", stderr="")
    with patch("arbora.adapters.desktop.require_windows", return_value=None), patch(
        "arbora.adapters.desktop.run_powershell", return_value=fake
    ) as mocked:
        result = DesktopAdapter().execute("inspect_windows_update", {}, dry_run=False)
    assert result.ok
    assert "no windows update" in result.output.lower()
    command = str(mocked.call_args[0][0]).lower()
    assert "get-hotfix" in command
    assert "installedon" in command
    assert "install-windowsupdate" not in command
    assert "wuauclt" not in command
    assert "usoclient" not in command
    assert "ms-settings:windowsupdate" not in command


def test_inspect_windows_update_withholds_secret_like_output():
    fake = ShellOutcome(ok=True, stdout="password=hunter2", stderr="")
    with patch("arbora.adapters.desktop.require_windows", return_value=None), patch(
        "arbora.adapters.desktop.run_powershell", return_value=fake
    ):
        result = DesktopAdapter().execute("inspect_windows_update", {}, dry_run=False)
    assert result.ok is False
    assert "secret" in (result.error or "").lower()


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
