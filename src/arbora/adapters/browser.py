"""Browser adapter powered by Playwright (broker-gated only).

Extracted page text is data for the user/planner — never auto-executed as tools.
Only http/https URLs are accepted.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from arbora.adapters.files import resolve_user_path
from arbora.adapters.powershell import DEFAULT_MAX_OUTPUT_CHARS
from arbora.core.types import StepResult, new_id

_MAX_TEXT = DEFAULT_MAX_OUTPUT_CHARS
_MAX_LINKS = 40


def validate_http_url(url: str) -> str | None:
    """Return an error message if URL is invalid; otherwise None."""
    raw = (url or "").strip()
    if not raw:
        return "URL is required"
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        return "Only http and https URLs are allowed"
    if not parsed.netloc:
        return "URL must include a host"
    return None


def _truncate(text: str, limit: int = _MAX_TEXT) -> str:
    text = text.strip()
    if limit <= 0 or len(text) <= limit:
        return text
    omitted = len(text) - limit
    return text[:limit] + f"\n...[truncated {omitted} chars]"


class BrowserAdapter:
    name = "browser"

    def __init__(self) -> None:
        self._playwright = None
        self._browser = None
        self._page = None
        self._last_url: str | None = None
        self._last_title: str | None = None
        self._last_text: str | None = None
        self._last_links: list[tuple[str, str]] = []

    def execute(self, action: str, args: dict[str, Any], *, dry_run: bool = False) -> StepResult:
        if action == "open_url":
            return self._open_url(
                str(args.get("url", "")),
                headed=bool(args.get("headed", False)),
                dry_run=dry_run,
            )
        if action == "get_title":
            return self._get_title(dry_run=dry_run)
        if action == "extract_text":
            return self._extract_text(dry_run=dry_run)
        if action == "extract_links":
            return self._extract_links(dry_run=dry_run)
        if action == "save_brief":
            return self._save_brief(
                str(args.get("path", "")),
                topic=str(args.get("topic", "")),
                dry_run=dry_run,
            )
        if action == "click":
            return self._click(
                str(args.get("selector", "")),
                button=str(args.get("button", "left")),
                timeout_ms=int(args.get("timeout_ms", 10_000)),
                dry_run=dry_run,
            )
        if action == "type_text":
            return self._type_text(
                str(args.get("selector", "")),
                text=str(args.get("text", "")),
                clear_first=bool(args.get("clear_first", True)),
                timeout_ms=int(args.get("timeout_ms", 10_000)),
                dry_run=dry_run,
            )
        if action == "wait_for":
            return self._wait_for(
                selector=str(args.get("selector", "")),
                state=str(args.get("state", "visible")),
                timeout_ms=int(args.get("timeout_ms", 10_000)),
                dry_run=dry_run,
            )
        if action == "snapshot":
            return self._snapshot(
                str(args.get("path", "")),
                full_page=bool(args.get("full_page", True)),
                dry_run=dry_run,
            )
        if action == "close":
            return self._close(dry_run=dry_run)
        return StepResult(
            step_id=new_id("res_"),
            ok=False,
            output="",
            error=f"Unknown browser action '{action}'",
            dry_run=dry_run,
        )

    def _ensure_playwright(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            ) from exc
        return sync_playwright

    def _ensure_page(self, *, headed: bool = False):
        if self._page is not None:
            return self._page
        sync_playwright = self._ensure_playwright()
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=not headed)
        self._page = self._browser.new_page()
        return self._page

    def _open_url(self, url: str, *, headed: bool, dry_run: bool) -> StepResult:
        err = validate_http_url(url)
        if err:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=err, dry_run=dry_run)
        if dry_run:
            mode = "headed" if headed else "headless"
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would open ({mode}): {url}",
                dry_run=True,
            )
        try:
            page = self._ensure_page(headed=headed)
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            self._last_url = page.url
            self._last_title = page.title()
            self._last_text = None
            self._last_links = []
        except Exception as exc:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Failed to open URL: {exc}",
            )
        return StepResult(
            step_id=new_id("res_"),
            ok=True,
            output=f"Opened: {self._last_url}\nTitle: {self._last_title}",
        )

    def _get_title(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output="[dry-run] Would read page title",
                dry_run=True,
            )
        if self._page is None:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="No page open. Call open_url first.",
            )
        try:
            title = self._page.title()
            self._last_title = title
        except Exception as exc:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=str(exc))
        return StepResult(step_id=new_id("res_"), ok=True, output=title or "(empty title)")

    def _extract_text(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output="[dry-run] Would extract visible page text",
                dry_run=True,
            )
        if self._page is None:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="No page open. Call open_url first.",
            )
        try:
            # Prefer article/main; fall back to body inner_text.
            text = self._page.evaluate(
                """() => {
                  const node = document.querySelector('article, main, [role="main"]') || document.body;
                  return node ? node.innerText : '';
                }"""
            )
            text = _truncate(re.sub(r"\n{3,}", "\n\n", str(text or "")))
            self._last_text = text
        except Exception as exc:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=str(exc))
        return StepResult(step_id=new_id("res_"), ok=True, output=text or "(no text)")

    def _extract_links(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output="[dry-run] Would extract page links",
                dry_run=True,
            )
        if self._page is None:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="No page open. Call open_url first.",
            )
        try:
            raw_links = self._page.evaluate(
                """() => Array.from(document.querySelectorAll('a[href]')).map(a => ({
                  href: a.href,
                  text: (a.innerText || '').trim().slice(0, 120)
                }))"""
            )
            links: list[tuple[str, str]] = []
            seen: set[str] = set()
            for item in raw_links or []:
                href = str(item.get("href", "")).strip()
                if not href.startswith(("http://", "https://")):
                    continue
                if href in seen:
                    continue
                seen.add(href)
                links.append((href, str(item.get("text", ""))))
                if len(links) >= _MAX_LINKS:
                    break
            self._last_links = links
        except Exception as exc:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=str(exc))
        lines = [f"{text or '(no label)'} — {href}" for href, text in links]
        return StepResult(
            step_id=new_id("res_"),
            ok=True,
            output="\n".join(lines) if lines else "(no links)",
        )

    def _save_brief(self, path: str, *, topic: str, dry_run: bool) -> StepResult:
        if not path.strip():
            path = str(resolve_user_path("~/ArboraBriefs") / "brief.md")
        else:
            path = str(resolve_user_path(path))
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would save research brief to {path}",
                dry_run=True,
            )
        if not self._last_url and self._page is None:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="Nothing to save. open_url (and preferably extract_*) first.",
            )
        # Refresh caches if needed.
        if self._page is not None:
            if self._last_title is None:
                self._get_title(dry_run=False)
            if self._last_text is None:
                self._extract_text(dry_run=False)
            if not self._last_links:
                self._extract_links(dry_run=False)

        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        title = self._last_title or "Untitled"
        url = self._last_url or ""
        excerpt = (self._last_text or "")[:4000]
        link_lines = "\n".join(f"- [{t or href}]({href})" for href, t in self._last_links[:20])
        body = (
            f"# Research brief{f': {topic}' if topic else ''}\n\n"
            f"- **Saved:** {stamp}\n"
            f"- **Source title:** {title}\n"
            f"- **URL:** {url}\n\n"
            f"## Excerpt\n\n{excerpt or '(no excerpt)'}\n\n"
            f"## Links\n\n{link_lines or '(none)'}\n\n"
            f"---\n_Page text is untrusted data; Arbora does not execute it as tools._\n"
        )
        try:
            out = resolve_user_path(path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(body, encoding="utf-8")
        except OSError as exc:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Failed to write brief: {exc}",
            )
        return StepResult(step_id=new_id("res_"), ok=True, output=f"Saved brief: {out}")

    def _require_page(self, *, dry_run: bool) -> StepResult | None:
        if dry_run:
            return None
        if self._page is None:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="No page open. Call open_url first.",
            )
        return None

    @staticmethod
    def _require_selector(selector: str) -> str | None:
        sel = (selector or "").strip()
        if not sel:
            return "CSS selector is required"
        if len(sel) > 500:
            return "Selector too long"
        return None

    def _click(
        self,
        selector: str,
        *,
        button: str,
        timeout_ms: int,
        dry_run: bool,
    ) -> StepResult:
        err = self._require_selector(selector)
        if err:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=err, dry_run=dry_run)
        btn = button if button in {"left", "right", "middle"} else "left"
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would click ({btn}): {selector}",
                dry_run=True,
            )
        missing = self._require_page(dry_run=False)
        if missing:
            return missing
        try:
            assert self._page is not None
            self._page.click(selector, button=btn, timeout=max(1_000, timeout_ms))
        except Exception as exc:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Click failed: {exc}",
            )
        return StepResult(step_id=new_id("res_"), ok=True, output=f"Clicked ({btn}): {selector}")

    def _type_text(
        self,
        selector: str,
        *,
        text: str,
        clear_first: bool,
        timeout_ms: int,
        dry_run: bool,
    ) -> StepResult:
        err = self._require_selector(selector)
        if err:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=err, dry_run=dry_run)
        if dry_run:
            preview = text if len(text) <= 80 else text[:80] + "…"
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would type into {selector}: {preview!r}",
                dry_run=True,
            )
        missing = self._require_page(dry_run=False)
        if missing:
            return missing
        try:
            assert self._page is not None
            locator = self._page.locator(selector).first
            locator.wait_for(state="visible", timeout=max(1_000, timeout_ms))
            if clear_first:
                locator.fill(text)
            else:
                locator.type(text)
        except Exception as exc:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Type failed: {exc}",
            )
        return StepResult(
            step_id=new_id("res_"),
            ok=True,
            output=f"Typed {len(text)} chars into {selector}",
        )

    def _wait_for(
        self,
        *,
        selector: str,
        state: str,
        timeout_ms: int,
        dry_run: bool,
    ) -> StepResult:
        err = self._require_selector(selector)
        if err:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=err, dry_run=dry_run)
        wait_state = state if state in {"attached", "detached", "visible", "hidden"} else "visible"
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would wait for {selector} state={wait_state}",
                dry_run=True,
            )
        missing = self._require_page(dry_run=False)
        if missing:
            return missing
        try:
            assert self._page is not None
            self._page.locator(selector).first.wait_for(
                state=wait_state,
                timeout=max(1_000, timeout_ms),
            )
        except Exception as exc:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Wait failed: {exc}",
            )
        return StepResult(
            step_id=new_id("res_"),
            ok=True,
            output=f"Wait satisfied: {selector} ({wait_state})",
        )

    def _snapshot(self, path: str, *, full_page: bool, dry_run: bool) -> StepResult:
        if not path.strip():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            path = str(resolve_user_path("~/ArboraBriefs") / f"snapshot-{stamp}.png")
        else:
            path = str(resolve_user_path(path))
        if not path.lower().endswith((".png", ".jpg", ".jpeg")):
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="Snapshot path must end with .png or .jpg",
                dry_run=dry_run,
            )
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would save screenshot to {path}",
                dry_run=True,
            )
        missing = self._require_page(dry_run=False)
        if missing:
            return missing
        try:
            assert self._page is not None
            out = resolve_user_path(path)
            out.parent.mkdir(parents=True, exist_ok=True)
            self._page.screenshot(path=str(out), full_page=full_page)
        except Exception as exc:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Snapshot failed: {exc}",
            )
        return StepResult(step_id=new_id("res_"), ok=True, output=f"Saved snapshot: {out}")

    def _close(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output="[dry-run] Would close browser session",
                dry_run=True,
            )
        try:
            if self._browser is not None:
                self._browser.close()
            if self._playwright is not None:
                self._playwright.stop()
        except Exception as exc:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=str(exc))
        finally:
            self._playwright = None
            self._browser = None
            self._page = None
        return StepResult(step_id=new_id("res_"), ok=True, output="Browser session closed")
