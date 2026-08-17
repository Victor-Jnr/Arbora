# 027 — Research journey snapshot

- **Date:** 2026-08-17
- **Commit subject:** Add page snapshot step to the research journey
- **Stage:** Stage 3

## Summary

The built-in research journey and example workflow pack now save a local PNG snapshot of the page before writing the cited brief.

## Changes

- Added `browser.snapshot` step to `_research_plan` in the planner
- Updated `workflows/research-example.json` with a snapshot step
- Research plan shape test asserts snapshot is present

## Safety / permissions

- Snapshot is a `mutate` step — still requires user approval
- Page content remains untrusted data; snapshot is for human review only

## How to verify

```powershell
arbora --provider echo --goal "research https://example.com" --yes
pytest tests/test_browser_adapter.py -k research_plan_shape
```
