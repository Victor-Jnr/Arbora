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


class FilesAdapter:
    name = "files"

    def execute(self, action: str, args: dict[str, Any], *, dry_run: bool = False) -> StepResult:
        if action == "list_directory":
            return self._list_directory(Path(str(args.get("path", "."))), dry_run=dry_run)
        if action == "ensure_directory":
            return self._ensure_directory(Path(str(args.get("path", ""))), dry_run=dry_run)
        if action == "write_text":
            return self._write_text(
                Path(str(args.get("path", ""))),
                str(args.get("content", "")),
                dry_run=dry_run,
            )
        if action == "preview_organise":
            return self._preview_organise(Path(str(args.get("path", ""))), dry_run=dry_run)
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
        entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        lines = []
        for entry in entries[:100]:
            kind = "dir" if entry.is_dir() else "file"
            lines.append(f"[{kind}] {entry.name}")
        if len(entries) > 100:
            lines.append(f"... and {len(entries) - 100} more")
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
        path.mkdir(parents=True, exist_ok=True)
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
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return StepResult(step_id=new_id("res_"), ok=True, output=f"Wrote {path}")

    def _preview_organise(self, path: Path, *, dry_run: bool) -> StepResult:
        # Classification is always non-mutating; dry_run only changes the label.
        if not path.exists() or not path.is_dir():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Cannot preview organise for {path}",
                dry_run=dry_run,
            )
        groups: dict[str, list[str]] = defaultdict(list)
        for entry in path.iterdir():
            if not entry.is_file():
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
