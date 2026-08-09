"""Browser adapter + research journey tests (Playwright mocked)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from arbora.adapters.browser import BrowserAdapter, validate_http_url
from arbora.cli.session import approve_all, build_runtime


def test_validate_http_url():
    assert validate_http_url("https://example.com/path") is None
    assert validate_http_url("http://example.com") is None
    assert validate_http_url("file:///etc/passwd") is not None
    assert validate_http_url("javascript:alert(1)") is not None
    assert validate_http_url("") is not None


def test_browser_dry_run_actions():
    adapter = BrowserAdapter()
    opened = adapter.execute("open_url", {"url": "https://example.com"}, dry_run=True)
    assert opened.ok and opened.dry_run
    assert "example.com" in opened.output
    title = adapter.execute("get_title", {}, dry_run=True)
    assert title.ok and title.dry_run
    text = adapter.execute("extract_text", {}, dry_run=True)
    assert text.ok
    links = adapter.execute("extract_links", {}, dry_run=True)
    assert links.ok
    brief = adapter.execute(
        "save_brief",
        {"path": str(Path.home() / "ArboraBriefs" / "t.md"), "topic": "demo"},
        dry_run=True,
    )
    assert brief.ok and brief.dry_run


def test_open_url_rejects_non_http():
    adapter = BrowserAdapter()
    result = adapter.execute("open_url", {"url": "ftp://files.example"}, dry_run=False)
    assert result.ok is False
    assert "http" in (result.error or "").lower()


def test_research_plan_shape():
    runtime = build_runtime(memory_root=Path("."), provider="echo")
    plan = runtime.planner.plan("research https://example.com about trees")
    assert any(s.adapter == "browser" and s.action == "open_url" for s in plan.steps)
    assert any(s.action == "save_brief" for s in plan.steps)
    assert any(s.action == "extract_text" for s in plan.steps)
    assert any(s.adapter == "files" and s.action == "ensure_directory" for s in plan.steps)
    assert "untrusted" in plan.rationale.lower()


def test_research_look_up_phrasing():
    runtime = build_runtime(memory_root=Path("."), provider="echo")
    plan = runtime.planner.plan("look up https://example.org")
    assert any(s.action == "open_url" for s in plan.steps)


def test_research_plan_dry_run_execute(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    plan = runtime.planner.plan("summarise https://example.org")
    results = runtime.broker.execute_plan(plan, approve_all(plan), dry_run=True)
    assert results
    assert all(r.ok for r in results)
    assert all(r.dry_run for r in results)


def test_browser_open_and_extract_with_mock(tmp_path: Path):
    adapter = BrowserAdapter()
    fake_page = MagicMock()
    fake_page.url = "https://example.com/"
    fake_page.title.return_value = "Example Domain"
    fake_page.evaluate.side_effect = [
        "Hello from the page.\n\nMore text.",
        [{"href": "https://example.com/a", "text": "A"}, {"href": "https://other.test/b", "text": "B"}],
    ]
    fake_browser = MagicMock()
    fake_browser.new_page.return_value = fake_page
    fake_pw = MagicMock()
    fake_pw.chromium.launch.return_value = fake_browser
    fake_cm = MagicMock()
    fake_cm.start.return_value = fake_pw

    with patch.object(adapter, "_ensure_playwright", return_value=lambda: fake_cm):
        opened = adapter.execute("open_url", {"url": "https://example.com"}, dry_run=False)
        assert opened.ok
        title = adapter.execute("get_title", {}, dry_run=False)
        assert title.output == "Example Domain"
        text = adapter.execute("extract_text", {}, dry_run=False)
        assert "Hello from the page" in text.output
        links = adapter.execute("extract_links", {}, dry_run=False)
        assert "https://example.com/a" in links.output
        brief_path = tmp_path / "brief.md"
        saved = adapter.execute(
            "save_brief",
            {"path": str(brief_path), "topic": "example"},
            dry_run=False,
        )
        assert saved.ok
        assert brief_path.exists()
        content = brief_path.read_text(encoding="utf-8")
        assert "Example Domain" in content
        assert "untrusted data" in content.lower()
