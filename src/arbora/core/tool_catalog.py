"""Allowed adapter actions for plans, workflow packs, and provider JSON."""

from __future__ import annotations

ALLOWED_ACTIONS: dict[str, frozenset[str]] = {
    "desktop": frozenset(
        {
            "list_running_apps",
            "launch_app",
            "focus_window",
            "inspect_clipboard",
            "save_clipboard_text",
            "speak_text",
            "capture_screenshot",
            "inspect_network",
            "inspect_battery",
            "close_window",
            "open_in_browser",
            "inspect_printers",
            "inspect_startup",
            "inspect_default_browser",
            "inspect_display",
            "inspect_windows_update",
            "inspect_timezone",
            "inspect_theme",
            "inspect_volume",
            "inspect_wallpaper",
            "inspect_idle",
        }
    ),
    "files": frozenset(
        {
            "list_directory",
            "ensure_directory",
            "write_text",
            "preview_organise",
            "apply_organise",
            "undo_last_organise",
            "open_in_explorer",
            "inspect_recycle_bin",
            "empty_recycle_bin",
            "search_by_name",
            "list_recent",
            "inspect_user_temp",
            "clean_user_temp",
            "preview_copy_move",
            "copy_file",
            "move_file",
            "inspect_old_files",
            "delete_old_files",
        }
    ),
    "terminal": frozenset({"run_powershell"}),
    "browser": frozenset(
        {
            "open_url",
            "get_title",
            "extract_text",
            "extract_links",
            "save_brief",
            "click",
            "type_text",
            "wait_for",
            "snapshot",
            "close",
        }
    ),
}
