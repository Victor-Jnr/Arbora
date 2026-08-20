"""Allowed adapter actions for plans, workflow packs, and provider JSON."""

from __future__ import annotations

ALLOWED_ACTIONS: dict[str, frozenset[str]] = {
    "desktop": frozenset({"list_running_apps", "launch_app", "focus_window"}),
    "files": frozenset(
        {
            "list_directory",
            "ensure_directory",
            "write_text",
            "preview_organise",
            "apply_organise",
            "undo_last_organise",
            "open_in_explorer",
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
