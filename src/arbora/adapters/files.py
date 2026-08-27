"""Files and folders adapter with preview-first organisation helpers."""

from __future__ import annotations

import fnmatch
import os
import shutil
import sys
import tempfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from arbora.adapters.file_undo import (
    FileMoveRecord,
    UndoBatch,
    UndoJournalLoader,
    UndoJournalStore,
    append_batch,
    pop_last_batch,
    utc_now_iso,
)
from arbora.adapters.powershell import require_windows, run_powershell
from arbora.core.types import StepResult, new_id

_EXTENSION_GROUPS = {
    "documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".odt"},
    "images": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"},
    "archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "installers": {".exe", ".msi", ".msix", ".appx"},
    "media": {".mp3", ".mp4", ".wav", ".mkv", ".mov", ".avi"},
}


def resolve_user_path(raw: str) -> Path:
    """Expand ~ and environment variables, then resolve (non-strict)."""
    text = str(raw or "").strip() or "."
    return Path(text).expanduser().resolve(strict=False)


def classify_bucket(path: Path) -> str:
    suffix = path.suffix.lower()
    for name, extensions in _EXTENSION_GROUPS.items():
        if suffix in extensions:
            return name
    return "other"


def plan_organise_moves(root: Path) -> list[tuple[str, Path, Path]]:
    """Return (bucket, source, destination) moves for files directly under root."""
    if not root.exists() or not root.is_dir():
        return []
    moves: list[tuple[str, Path, Path]] = []
    try:
        entries = list(root.iterdir())
    except (PermissionError, OSError):
        return []
    for entry in entries:
        try:
            if not entry.is_file():
                continue
        except OSError:
            continue
        bucket = classify_bucket(entry)
        destination = root / bucket / entry.name
        if destination.resolve(strict=False) == entry.resolve(strict=False):
            continue
        moves.append((bucket, entry, destination))
    return moves


DEFAULT_SEARCH_MAX_DEPTH = 3
DEFAULT_SEARCH_MAX_RESULTS = 50
DEFAULT_RECENT_MAX_DEPTH = 2
DEFAULT_RECENT_MAX_RESULTS = 20
DEFAULT_RECENT_WALK_CAP = 2000
DEFAULT_OLD_DAYS = 30
DEFAULT_OLD_MAX_RESULTS = 200
MIN_OLD_DAYS = 1
MAX_OLD_DAYS = 3650


def is_protected_search_root(path: Path) -> bool:
    """Refuse walks under the Windows directory."""
    windir = Path(os.environ.get("WINDIR", r"C:\Windows")).expanduser().resolve(strict=False)
    try:
        resolved = path.expanduser().resolve(strict=False)
    except OSError:
        return True
    if resolved == windir:
        return True
    return windir in resolved.parents


def _is_drive_root(path: Path) -> bool:
    resolved = path.expanduser().resolve(strict=False)
    return resolved.parent == resolved


def _name_glob(pattern: str) -> str:
    raw = (pattern or "*").strip() or "*"
    if not any(char in raw for char in "*?["):
        return f"*{raw}*"
    return raw


def search_files_by_name(
    root: Path,
    pattern: str,
    *,
    max_depth: int = DEFAULT_SEARCH_MAX_DEPTH,
    max_results: int = DEFAULT_SEARCH_MAX_RESULTS,
) -> list[Path]:
    """Match file names under root, capped so C:\\ walks cannot hang the broker."""
    if max_depth < 0 or max_results < 1:
        return []
    if is_protected_search_root(root):
        return []
    if not root.exists() or not root.is_dir():
        return []
    depth_cap = 1 if _is_drive_root(root) else max_depth
    needle = _name_glob(pattern).lower()
    matches: list[Path] = []

    def walk(current: Path, depth: int) -> None:
        if len(matches) >= max_results:
            return
        try:
            entries = list(current.iterdir())
        except (PermissionError, OSError):
            return
        for entry in entries:
            if len(matches) >= max_results:
                return
            try:
                if entry.is_symlink():
                    continue
                if entry.is_file() and fnmatch.fnmatch(entry.name.lower(), needle):
                    matches.append(entry)
                elif entry.is_dir() and depth < depth_cap:
                    walk(entry, depth + 1)
            except OSError:
                continue

    walk(root, 0)
    return matches


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{round(size / 1024, 1)} KB"
    return f"{round(size / (1024 * 1024), 2)} MB"


def resolve_transfer_destination(source: Path, destination: Path) -> Path:
    """If destination is an existing directory, place the file under it."""
    if destination.exists() and destination.is_dir():
        return destination / source.name
    return destination


def list_recent_files(
    root: Path,
    *,
    max_depth: int = DEFAULT_RECENT_MAX_DEPTH,
    max_results: int = DEFAULT_RECENT_MAX_RESULTS,
    walk_cap: int = DEFAULT_RECENT_WALK_CAP,
) -> list[tuple[Path, float, int]]:
    """Return (path, mtime, size) for newest files under root, depth-capped."""
    if max_depth < 0 or max_results < 1 or walk_cap < 1:
        return []
    if is_protected_search_root(root):
        return []
    if not root.exists() or not root.is_dir():
        return []
    depth_cap = 1 if _is_drive_root(root) else max_depth
    found: list[tuple[Path, float, int]] = []

    def walk(current: Path, depth: int) -> None:
        if len(found) >= walk_cap:
            return
        try:
            entries = list(current.iterdir())
        except (PermissionError, OSError):
            return
        for entry in entries:
            if len(found) >= walk_cap:
                return
            try:
                if entry.is_symlink():
                    continue
                if entry.is_file():
                    stat = entry.stat()
                    found.append((entry, stat.st_mtime, stat.st_size))
                elif entry.is_dir() and depth < depth_cap:
                    walk(entry, depth + 1)
            except OSError:
                continue

    walk(root, 0)
    found.sort(key=lambda row: row[1], reverse=True)
    return found[:max_results]


def clamp_older_than_days(raw: Any, default: int = DEFAULT_OLD_DAYS) -> int:
    try:
        days = int(raw)
    except (TypeError, ValueError):
        days = default
    return max(MIN_OLD_DAYS, min(days, MAX_OLD_DAYS))


def is_protected_delete_root(path: Path) -> bool:
    """Refuse Windows directory walks and drive-root deletes."""
    return is_protected_search_root(path) or _is_drive_root(path)


def list_old_files(
    root: Path,
    *,
    older_than_days: int,
    max_results: int = DEFAULT_OLD_MAX_RESULTS,
) -> list[tuple[Path, float, int]]:
    """Return (path, mtime, size) for top-level files older than N days, oldest first."""
    days = clamp_older_than_days(older_than_days)
    if max_results < 1:
        return []
    if is_protected_delete_root(root):
        return []
    if not root.exists() or not root.is_dir():
        return []
    cutoff = datetime.now().timestamp() - days * 86400
    found: list[tuple[Path, float, int]] = []
    try:
        entries = list(root.iterdir())
    except (PermissionError, OSError):
        return []
    for entry in entries:
        try:
            if entry.is_symlink() or not entry.is_file():
                continue
            stat = entry.stat()
            if stat.st_mtime <= cutoff:
                found.append((entry, stat.st_mtime, stat.st_size))
        except OSError:
            continue
    found.sort(key=lambda row: row[1])
    return found[:max_results]


def format_old_files_report(
    root: Path,
    rows: list[tuple[Path, float, int]],
    *,
    older_than_days: int,
    max_results: int,
) -> str:
    lines = [
        (
            f"Top-level files in {root} older than {older_than_days} day(s) "
            f"(oldest first, cap {max_results})"
        )
    ]
    if not rows:
        lines.append("(no matching files)")
        return "\n".join(lines)
    for item, mtime, size in rows:
        stamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        lines.append(f"  {item.name}  {stamp}  {_format_size(size)}")
    if len(rows) >= max_results:
        lines.append(f"... stopped at {max_results} files")
    return "\n".join(lines)


def user_temp_dir() -> Path:
    """The current user's TEMP folder — never C:\\Windows\\Temp unless that is TEMP."""
    raw = os.environ.get("TEMP") or os.environ.get("TMP") or tempfile.gettempdir()
    return Path(raw).expanduser().resolve(strict=False)


def list_temp_toplevel(root: Path) -> tuple[list[Path], list[Path]]:
    """Return (files, directories) immediately under the temp folder."""
    files: list[Path] = []
    directories: list[Path] = []
    if not root.exists() or not root.is_dir():
        return files, directories
    try:
        entries = list(root.iterdir())
    except (PermissionError, OSError):
        return files, directories
    for entry in entries:
        try:
            if entry.is_dir() and not entry.is_symlink():
                directories.append(entry)
            elif entry.is_file() or entry.is_symlink():
                files.append(entry)
        except OSError:
            continue
    return files, directories


class FilesAdapter:
    name = "files"

    def __init__(
        self,
        *,
        undo_loader: UndoJournalLoader | None = None,
        undo_store: UndoJournalStore | None = None,
    ) -> None:
        self._undo_loader = undo_loader
        self._undo_store = undo_store

    def execute(self, action: str, args: dict[str, Any], *, dry_run: bool = False) -> StepResult:
        if action == "list_directory":
            return self._list_directory(resolve_user_path(str(args.get("path", "."))), dry_run=dry_run)
        if action == "ensure_directory":
            return self._ensure_directory(resolve_user_path(str(args.get("path", ""))), dry_run=dry_run)
        if action == "write_text":
            return self._write_text(
                resolve_user_path(str(args.get("path", ""))),
                str(args.get("content", "")),
                dry_run=dry_run,
            )
        if action == "preview_organise":
            return self._preview_organise(resolve_user_path(str(args.get("path", ""))), dry_run=dry_run)
        if action == "apply_organise":
            return self._apply_organise(resolve_user_path(str(args.get("path", ""))), dry_run=dry_run)
        if action == "undo_last_organise":
            return self._undo_last_organise(dry_run=dry_run)
        if action == "open_in_explorer":
            raw = str(args.get("path", "")).strip()
            if not raw:
                return StepResult(
                    step_id=new_id("res_"),
                    ok=False,
                    output="",
                    error="open_in_explorer requires args.path",
                    dry_run=dry_run,
                )
            return self._open_in_explorer(resolve_user_path(raw), dry_run=dry_run)
        if action == "inspect_recycle_bin":
            return self._inspect_recycle_bin(dry_run=dry_run)
        if action == "empty_recycle_bin":
            return self._empty_recycle_bin(dry_run=dry_run)
        if action == "inspect_user_temp":
            return self._inspect_user_temp(dry_run=dry_run)
        if action == "clean_user_temp":
            return self._clean_user_temp(dry_run=dry_run)
        if action == "search_by_name":
            raw = str(args.get("path", "")).strip()
            if not raw:
                return StepResult(
                    step_id=new_id("res_"),
                    ok=False,
                    output="",
                    error="search_by_name requires args.path",
                    dry_run=dry_run,
                )
            try:
                max_depth = int(args.get("max_depth", DEFAULT_SEARCH_MAX_DEPTH) or DEFAULT_SEARCH_MAX_DEPTH)
            except (TypeError, ValueError):
                max_depth = DEFAULT_SEARCH_MAX_DEPTH
            try:
                max_results = int(args.get("max_results", DEFAULT_SEARCH_MAX_RESULTS) or DEFAULT_SEARCH_MAX_RESULTS)
            except (TypeError, ValueError):
                max_results = DEFAULT_SEARCH_MAX_RESULTS
            return self._search_by_name(
                resolve_user_path(raw),
                str(args.get("pattern", "*")),
                max_depth=max_depth,
                max_results=max_results,
                dry_run=dry_run,
            )
        if action == "list_recent":
            raw = str(args.get("path", "")).strip()
            if not raw:
                return StepResult(
                    step_id=new_id("res_"),
                    ok=False,
                    output="",
                    error="list_recent requires args.path",
                    dry_run=dry_run,
                )
            try:
                max_depth = int(args.get("max_depth", DEFAULT_RECENT_MAX_DEPTH) or DEFAULT_RECENT_MAX_DEPTH)
            except (TypeError, ValueError):
                max_depth = DEFAULT_RECENT_MAX_DEPTH
            try:
                max_results = int(args.get("max_results", DEFAULT_RECENT_MAX_RESULTS) or DEFAULT_RECENT_MAX_RESULTS)
            except (TypeError, ValueError):
                max_results = DEFAULT_RECENT_MAX_RESULTS
            return self._list_recent(
                resolve_user_path(raw),
                max_depth=max_depth,
                max_results=max_results,
                dry_run=dry_run,
            )
        if action == "preview_copy_move":
            return self._preview_copy_move(
                str(args.get("source", "")),
                str(args.get("destination", "")),
                str(args.get("operation", "copy")),
                dry_run=dry_run,
            )
        if action == "copy_file":
            return self._apply_copy_move(
                str(args.get("source", "")),
                str(args.get("destination", "")),
                operation="copy",
                dry_run=dry_run,
            )
        if action == "move_file":
            return self._apply_copy_move(
                str(args.get("source", "")),
                str(args.get("destination", "")),
                operation="move",
                dry_run=dry_run,
            )
        if action == "inspect_old_files":
            raw = str(args.get("path", "")).strip()
            if not raw:
                return StepResult(
                    step_id=new_id("res_"),
                    ok=False,
                    output="",
                    error="inspect_old_files requires args.path",
                    dry_run=dry_run,
                )
            try:
                max_results = int(args.get("max_results", DEFAULT_OLD_MAX_RESULTS) or DEFAULT_OLD_MAX_RESULTS)
            except (TypeError, ValueError):
                max_results = DEFAULT_OLD_MAX_RESULTS
            return self._inspect_old_files(
                resolve_user_path(raw),
                older_than_days=clamp_older_than_days(args.get("older_than_days", DEFAULT_OLD_DAYS)),
                max_results=max_results,
                dry_run=dry_run,
            )
        if action == "delete_old_files":
            raw = str(args.get("path", "")).strip()
            if not raw:
                return StepResult(
                    step_id=new_id("res_"),
                    ok=False,
                    output="",
                    error="delete_old_files requires args.path",
                    dry_run=dry_run,
                )
            try:
                max_results = int(args.get("max_results", DEFAULT_OLD_MAX_RESULTS) or DEFAULT_OLD_MAX_RESULTS)
            except (TypeError, ValueError):
                max_results = DEFAULT_OLD_MAX_RESULTS
            return self._delete_old_files(
                resolve_user_path(raw),
                older_than_days=clamp_older_than_days(args.get("older_than_days", DEFAULT_OLD_DAYS)),
                max_results=max_results,
                dry_run=dry_run,
            )
        return StepResult(
            step_id=new_id("res_"),
            ok=False,
            output="",
            error=f"Unknown files action '{action}'",
            dry_run=dry_run,
        )

    def _list_directory(self, path: Path, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would list {path}",
                dry_run=True,
            )
        if not path.exists():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Path does not exist: {path}",
            )
        if not path.is_dir():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Not a directory: {path}",
            )
        try:
            entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Permission denied listing: {path}",
            )
        except OSError as exc:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Failed to list {path}: {exc}",
            )

        lines: list[str] = []
        skipped = 0
        for entry in entries[:100]:
            try:
                kind = "dir" if entry.is_dir() else "file"
                lines.append(f"[{kind}] {entry.name}")
            except OSError:
                skipped += 1
        if len(entries) > 100:
            lines.append(f"... and {len(entries) - 100} more")
        if skipped:
            lines.append(f"(skipped {skipped} inaccessible entries)")
        return StepResult(
            step_id=new_id("res_"),
            ok=True,
            output="\n".join(lines) if lines else "(empty)",
        )

    def _search_by_name(
        self,
        path: Path,
        pattern: str,
        *,
        max_depth: int,
        max_results: int,
        dry_run: bool,
    ) -> StepResult:
        glob = _name_glob(pattern)
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    f"[dry-run] Would search {path} for names matching {glob} "
                    f"(max_depth={max_depth}, max_results={max_results})"
                ),
                dry_run=True,
            )
        if is_protected_search_root(path):
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Refusing to search the Windows directory: {path}",
            )
        if not path.exists():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Path does not exist: {path}",
            )
        if not path.is_dir():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Not a directory: {path}",
            )
        matches = search_files_by_name(
            path, pattern, max_depth=max_depth, max_results=max_results
        )
        lines = [f"Search in {path} for {glob} (depth ≤ {max_depth}, cap {max_results})"]
        if not matches:
            lines.append("(no matches)")
        else:
            lines.extend(str(item) for item in matches)
            if len(matches) >= max_results:
                lines.append(f"... stopped at {max_results} matches")
        return StepResult(step_id=new_id("res_"), ok=True, output="\n".join(lines))

    def _list_recent(
        self,
        path: Path,
        *,
        max_depth: int,
        max_results: int,
        dry_run: bool,
    ) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    f"[dry-run] Would list the newest files in {path} "
                    f"(max_depth={max_depth}, max_results={max_results})"
                ),
                dry_run=True,
            )
        if is_protected_search_root(path):
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Refusing to list recent files in the Windows directory: {path}",
            )
        if not path.exists():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Path does not exist: {path}",
            )
        if not path.is_dir():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Not a directory: {path}",
            )
        rows = list_recent_files(path, max_depth=max_depth, max_results=max_results)
        header = (
            f"Newest files in {path} (mtime descending, depth ≤ {max_depth}, cap {max_results})"
        )
        lines = [header]
        if not rows:
            lines.append("(no files)")
        else:
            for item, mtime, size in rows:
                try:
                    rel = item.relative_to(path)
                except ValueError:
                    rel = Path(item.name)
                stamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                lines.append(f"  {stamp}  {_format_size(size):>8}  {rel}")
        return StepResult(step_id=new_id("res_"), ok=True, output="\n".join(lines))

    def _inspect_old_files(
        self,
        path: Path,
        *,
        older_than_days: int,
        max_results: int,
        dry_run: bool,
    ) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    f"[dry-run] Would list top-level files in {path} "
                    f"older than {older_than_days} day(s) (cap {max_results})"
                ),
                dry_run=True,
            )
        if is_protected_delete_root(path):
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Refusing to inspect old files in a protected path: {path}",
            )
        if not path.exists():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Path does not exist: {path}",
            )
        if not path.is_dir():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Not a directory: {path}",
            )
        rows = list_old_files(path, older_than_days=older_than_days, max_results=max_results)
        return StepResult(
            step_id=new_id("res_"),
            ok=True,
            output=format_old_files_report(
                path, rows, older_than_days=older_than_days, max_results=max_results
            ),
        )

    def _delete_old_files(
        self,
        path: Path,
        *,
        older_than_days: int,
        max_results: int,
        dry_run: bool,
    ) -> StepResult:
        if is_protected_delete_root(path):
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Refusing to delete old files in a protected path: {path}",
                dry_run=dry_run,
            )
        rows = list_old_files(path, older_than_days=older_than_days, max_results=max_results)
        if dry_run:
            names = ", ".join(item.name for item, _mtime, _size in rows[:20]) or "(none)"
            extra = f"; +{len(rows) - 20} more" if len(rows) > 20 else ""
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    f"[dry-run] Would delete {len(rows)} top-level file(s) in {path} "
                    f"older than {older_than_days} day(s): {names}{extra}"
                ),
                dry_run=True,
            )
        deleted = 0
        skipped = 0
        for item, _mtime, _size in rows:
            try:
                item.unlink()
                deleted += 1
            except OSError:
                skipped += 1
        return StepResult(
            step_id=new_id("res_"),
            ok=True,
            output=(
                f"Deleted {deleted} top-level file(s) in {path} older than "
                f"{older_than_days} day(s); skipped {skipped}"
            ),
        )

    def _prepare_copy_move(
        self, source_raw: str, destination_raw: str, operation: str, *, dry_run: bool
    ) -> tuple[Path, Path, str, StepResult | None]:
        op = (operation or "copy").strip().lower()
        if op not in {"copy", "move"}:
            op = "copy"
        if not source_raw.strip() or not destination_raw.strip():
            return (
                Path(),
                Path(),
                op,
                StepResult(
                    step_id=new_id("res_"),
                    ok=False,
                    output="",
                    error=f"{op}_file requires args.source and args.destination",
                    dry_run=dry_run,
                ),
            )
        source = resolve_user_path(source_raw)
        destination = resolve_transfer_destination(source, resolve_user_path(destination_raw))
        if is_protected_search_root(source) or is_protected_search_root(destination):
            return (
                source,
                destination,
                op,
                StepResult(
                    step_id=new_id("res_"),
                    ok=False,
                    output="",
                    error="Refusing to copy or move under the Windows directory",
                    dry_run=dry_run,
                ),
            )
        return source, destination, op, None

    def _preview_copy_move(
        self, source_raw: str, destination_raw: str, operation: str, *, dry_run: bool
    ) -> StepResult:
        source, destination, op, error = self._prepare_copy_move(
            source_raw, destination_raw, operation, dry_run=dry_run
        )
        if error is not None:
            return error
        verb = "Copy" if op == "copy" else "Move"
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would preview {op} {source} -> {destination}",
                dry_run=True,
            )
        if not source.exists():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Source does not exist: {source}",
            )
        if not source.is_file():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Source is not a file: {source}",
            )
        try:
            size = _format_size(source.stat().st_size)
        except OSError:
            size = "unknown size"
        dest_state = "exists (refusing overwrite)" if destination.exists() else "new file"
        lines = [
            f"{verb} preview",
            f"  source: {source} ({size})",
            f"  destination: {destination} ({dest_state})",
        ]
        if op == "move":
            lines.append("  undo: move can be reversed with undo last organise / undo last move")
        else:
            lines.append("  copy is not undone automatically (destination would be a new file)")
        return StepResult(step_id=new_id("res_"), ok=True, output="\n".join(lines), dry_run=dry_run)

    def _apply_copy_move(
        self, source_raw: str, destination_raw: str, *, operation: str, dry_run: bool
    ) -> StepResult:
        source, destination, op, error = self._prepare_copy_move(
            source_raw, destination_raw, operation, dry_run=dry_run
        )
        if error is not None:
            return error
        verb = "copy" if op == "copy" else "move"
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would {verb} {source} -> {destination}",
                dry_run=True,
            )
        if not source.exists():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Source does not exist: {source}",
            )
        if not source.is_file():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Source is not a file: {source}",
            )
        if source.resolve(strict=False) == destination.resolve(strict=False):
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="Source and destination are the same path",
            )
        if destination.exists():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Destination already exists: {destination}",
            )
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if op == "copy":
                shutil.copy2(str(source), str(destination))
                return StepResult(
                    step_id=new_id("res_"),
                    ok=True,
                    output=f"Copied {source} -> {destination}",
                )
            shutil.move(str(source), str(destination))
            batch = UndoBatch(
                batch_id=new_id("undo_"),
                root=str(source.parent),
                moves=tuple([FileMoveRecord(source=str(source), destination=str(destination))]),
                created_at=utc_now_iso(),
            )
            append_batch(self._undo_loader, self._undo_store, batch)
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"Moved {source} -> {destination}\nUndo batch recorded: {batch.batch_id}",
            )
        except PermissionError:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Permission denied during {verb} of {source}",
            )
        except OSError as exc:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Failed to {verb} {source}: {exc}",
            )

    def _ensure_directory(self, path: Path, *, dry_run: bool) -> StepResult:
        if not str(path):
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="ensure_directory requires args.path",
                dry_run=dry_run,
            )
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would ensure directory {path}",
                dry_run=True,
            )
        try:
            path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Permission denied creating directory: {path}",
            )
        except OSError as exc:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Failed to create directory {path}: {exc}",
            )
        return StepResult(step_id=new_id("res_"), ok=True, output=f"Directory ready: {path}")

    def _open_in_explorer(self, path: Path, *, dry_run: bool) -> StepResult:
        target = path if (not path.exists() or path.is_dir()) else path.parent
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would open {target} in Explorer",
                dry_run=True,
            )
        if sys.platform != "win32":
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="open_in_explorer is Windows-only",
            )
        if not path.exists():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Path does not exist: {path}",
            )
        target = path if path.is_dir() else path.parent
        try:
            os.startfile(target)  # type: ignore[attr-defined]
        except OSError as exc:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Failed to open Explorer: {exc}",
            )
        return StepResult(step_id=new_id("res_"), ok=True, output=f"Opened in Explorer: {target}")

    def _inspect_recycle_bin(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output="[dry-run] Would list Recycle Bin item names (read-only)",
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        command = (
            "$shell = New-Object -ComObject Shell.Application; "
            "$bin = $shell.NameSpace(10); "
            "if ($null -eq $bin) { 'Recycle Bin is not available.'; exit 0 }; "
            "$items = @($bin.Items()); "
            "'Recycle Bin items: ' + $items.Count; "
            "$items | Select-Object -First 25 | ForEach-Object { $_.Name } | Out-String"
        )
        outcome = run_powershell(command, timeout_seconds=30)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error,
            )
        return StepResult(
            step_id=new_id("res_"),
            ok=True,
            output=outcome.stdout or "(empty Recycle Bin)",
        )

    def _empty_recycle_bin(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output="[dry-run] Would empty the Recycle Bin (permanent for those items)",
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        command = (
            "Clear-RecycleBin -Force -ErrorAction Stop; "
            "'Recycle Bin emptied.'"
        )
        outcome = run_powershell(command, timeout_seconds=60)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error,
            )
        return StepResult(step_id=new_id("res_"), ok=True, output=outcome.stdout or "Recycle Bin emptied.")

    def _inspect_user_temp(self, *, dry_run: bool) -> StepResult:
        root = user_temp_dir()
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would list top-level files in user TEMP ({root})",
                dry_run=True,
            )
        if is_protected_search_root(root):
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Refusing to inspect Windows directory TEMP: {root}",
            )
        if not root.exists() or not root.is_dir():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"TEMP folder is missing: {root}",
            )
        files, directories = list_temp_toplevel(root)
        total_bytes = 0
        for item in files:
            try:
                total_bytes += item.stat().st_size
            except OSError:
                continue
        mb = round(total_bytes / (1024 * 1024), 2)
        lines = [
            f"User TEMP: {root}",
            f"Top-level files: {len(files)} ({mb} MB)",
            f"Top-level directories (kept on clean): {len(directories)}",
        ]
        sample = files[:40]
        if sample:
            lines.append("Sample files:")
            lines.extend(f"  {item.name}" for item in sample)
        if len(files) > 40:
            lines.append(f"... and {len(files) - 40} more files")
        if not files:
            lines.append("(no top-level files)")
        return StepResult(step_id=new_id("res_"), ok=True, output="\n".join(lines))

    def _clean_user_temp(self, *, dry_run: bool) -> StepResult:
        root = user_temp_dir()
        if is_protected_search_root(root):
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Refusing to clean Windows directory TEMP: {root}",
                dry_run=dry_run,
            )
        files, directories = list_temp_toplevel(root)
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    f"[dry-run] Would delete {len(files)} top-level files in {root}; "
                    f"{len(directories)} directories would be left in place"
                ),
                dry_run=True,
            )
        deleted = 0
        skipped = 0
        for item in files:
            try:
                item.unlink()
                deleted += 1
            except OSError:
                skipped += 1
        return StepResult(
            step_id=new_id("res_"),
            ok=True,
            output=(
                f"Deleted {deleted} top-level files in {root}; "
                f"skipped {skipped}; left {len(directories)} directories"
            ),
        )

    def _write_text(self, path: Path, content: str, *, dry_run: bool) -> StepResult:
        if not str(path):
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="write_text requires args.path",
                dry_run=dry_run,
            )
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would write {len(content)} chars to {path}",
                dry_run=True,
            )
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except PermissionError:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Permission denied writing: {path}",
            )
        except OSError as exc:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Failed to write {path}: {exc}",
            )
        return StepResult(step_id=new_id("res_"), ok=True, output=f"Wrote {path}")

    def _preview_organise(self, path: Path, *, dry_run: bool) -> StepResult:
        moves = plan_organise_moves(path)
        if not path.exists() or not path.is_dir():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Cannot preview organise for {path}",
                dry_run=dry_run,
            )

        groups: dict[str, list[str]] = defaultdict(list)
        for bucket, source, _destination in moves:
            groups[bucket].append(source.name)

        lines = [f"Organisation preview for {path}"]
        if dry_run:
            lines[0] = f"[dry-run] {lines[0]}"
        for bucket in sorted(groups):
            lines.append(f"  {bucket}/ ({len(groups[bucket])} files)")
            for name in groups[bucket][:8]:
                lines.append(f"    - {name}")
            if len(groups[bucket]) > 8:
                lines.append(f"    ... +{len(groups[bucket]) - 8} more")
        if len(lines) == 1:
            lines.append("  (no files to classify)")
        lines.append("")
        lines.append("Use apply_organise to move files, then undo_last_organise to reverse.")
        return StepResult(step_id=new_id("res_"), ok=True, output="\n".join(lines), dry_run=dry_run)

    def _apply_organise(self, path: Path, *, dry_run: bool) -> StepResult:
        if not path.exists() or not path.is_dir():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Cannot organise {path}",
                dry_run=dry_run,
            )
        moves = plan_organise_moves(path)
        if not moves:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"No files to organise under {path}",
                dry_run=dry_run,
            )
        if dry_run:
            lines = [f"[dry-run] Would move {len(moves)} file(s) under {path}:"]
            for bucket, source, destination in moves[:20]:
                lines.append(f"  {source.name} -> {bucket}/{source.name}")
            if len(moves) > 20:
                lines.append(f"  ... +{len(moves) - 20} more")
            return StepResult(step_id=new_id("res_"), ok=True, output="\n".join(lines), dry_run=True)

        applied: list[FileMoveRecord] = []
        lines = [f"Moved {len(moves)} file(s) under {path}:"]
        for bucket, source, destination in moves:
            try:
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    return StepResult(
                        step_id=new_id("res_"),
                        ok=False,
                        output="\n".join(lines),
                        error=f"Destination already exists: {destination}",
                    )
                shutil.move(str(source), str(destination))
                applied.append(FileMoveRecord(source=str(source), destination=str(destination)))
                lines.append(f"  {source.name} -> {bucket}/{source.name}")
            except PermissionError:
                return StepResult(
                    step_id=new_id("res_"),
                    ok=False,
                    output="\n".join(lines),
                    error=f"Permission denied moving {source}",
                )
            except OSError as exc:
                return StepResult(
                    step_id=new_id("res_"),
                    ok=False,
                    output="\n".join(lines),
                    error=f"Failed moving {source}: {exc}",
                )

        batch = UndoBatch(
            batch_id=new_id("undo_"),
            root=str(path),
            moves=tuple(applied),
            created_at=utc_now_iso(),
        )
        append_batch(self._undo_loader, self._undo_store, batch)
        lines.append(f"Undo batch recorded: {batch.batch_id}")
        return StepResult(step_id=new_id("res_"), ok=True, output="\n".join(lines))

    def _undo_last_organise(self, *, dry_run: bool) -> StepResult:
        batch = pop_last_batch(self._undo_loader, self._undo_store)
        if batch is None:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="No organise undo batch is available",
                dry_run=dry_run,
            )
        if dry_run:
            lines = [f"[dry-run] Would undo batch {batch.batch_id} ({len(batch.moves)} moves):"]
            for move in batch.moves[:20]:
                lines.append(f"  {move.destination} -> {move.source}")
            return StepResult(step_id=new_id("res_"), ok=True, output="\n".join(lines), dry_run=True)

        lines = [f"Undoing batch {batch.batch_id}:"]
        for move in batch.moves:
            src = Path(move.destination)
            dst = Path(move.source)
            try:
                if not src.exists():
                    return StepResult(
                        step_id=new_id("res_"),
                        ok=False,
                        output="\n".join(lines),
                        error=f"Missing moved file: {src}",
                    )
                dst.parent.mkdir(parents=True, exist_ok=True)
                if dst.exists():
                    return StepResult(
                        step_id=new_id("res_"),
                        ok=False,
                        output="\n".join(lines),
                        error=f"Cannot restore; destination exists: {dst}",
                    )
                shutil.move(str(src), str(dst))
                lines.append(f"  {src.name} -> {dst.parent}")
            except (PermissionError, OSError) as exc:
                return StepResult(
                    step_id=new_id("res_"),
                    ok=False,
                    output="\n".join(lines),
                    error=f"Failed undoing {src}: {exc}",
                )
        return StepResult(step_id=new_id("res_"), ok=True, output="\n".join(lines))
