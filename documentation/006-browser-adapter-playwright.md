# 006 — Browser adapter (Playwright)

- **Date:** 2026-08-07
- **Commit subject:** Add Playwright browser adapter and research journey
- **Stage:** Stage 1

## Summary

Arbora can open http(s) pages in Chromium via Playwright, extract title/text/links, and save a local cited brief — always through the permission broker.

## Changes

- Added `adapters/browser.py` (`open_url`, `get_title`, `extract_text`, `extract_links`, `save_brief`, `close`)
- Registered browser adapter in runtime
- Research journey in the planner for research/summarise/brief + URL goals
- `playwright` dependency; document Chromium install
- Tests with dry-run and mocked Playwright

## Safety / permissions

- Only http/https URLs
- Extracted page text is treated as untrusted data (noted in briefs)
- No credential/financial browser actions in this phase

## How to verify

```powershell
pip install -e ".[dev]"
playwright install chromium
pytest
arbora --provider echo --goal "research https://example.com" --yes
```
