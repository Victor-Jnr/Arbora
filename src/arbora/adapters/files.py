"""Files and folders adapter with preview-first organisation helpers."""

from __future__ import annotations

import os
import shutil
import sys
from collections import defaultdict
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
