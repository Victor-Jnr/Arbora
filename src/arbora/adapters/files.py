"""Files and folders adapter with preview-first organisation helpers."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

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


class FilesAdapter:
    name = "files"

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
        if not path.exists() or not path.is_dir():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Cannot preview organise for {path}",
                dry_run=dry_run,
            )
        try:
            entries = list(path.iterdir())
        except PermissionError:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Permission denied listing: {path}",
                dry_run=dry_run,
            )
        except OSError as exc:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Failed to list {path}: {exc}",
                dry_run=dry_run,
            )

        groups: dict[str, list[str]] = defaultdict(list)
        for entry in entries:
            try:
                if not entry.is_file():
                    continue
            except OSError:
                continue
            bucket = "other"
            suffix = entry.suffix.lower()
            for name, extensions in _EXTENSION_GROUPS.items():
                if suffix in extensions:
                    bucket = name
                    break
            groups[bucket].append(entry.name)

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
        return StepResult(step_id=new_id("res_"), ok=True, output="\n".join(lines), dry_run=dry_run)
