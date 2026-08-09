# 014 — Richer broker-gated browser actions

- **Date:** 2026-08-09
- **Commit subject:** Add click, type, wait, and snapshot browser actions
- **Stage:** Stage 2

## Summary

The Playwright browser adapter now supports broker-gated page interactions: `click`, `type_text`, `wait_for`, and `snapshot`, in addition to the existing research actions. Page text remains untrusted data.

## Changes

- Browser adapter: click / type_text / wait_for / snapshot with dry-run paths
- Planner `ALLOWED_ACTIONS` updated so model-proposed plans may use the new actions
- Tests for dry-run, selector validation, and mocked live interactions

## Safety / permissions

- All new actions still require broker approval (mutate sensitivity when planned)
- Only CSS selectors — no arbitrary script injection API
- Snapshot paths limited to image extensions under resolved user paths
- Extracted page text is still never auto-executed as tools

## How to verify

```powershell
pytest tests/test_browser_adapter.py
# Via a model plan or future journey using click/type_text after open_url
```
