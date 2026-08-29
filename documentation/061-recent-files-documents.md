# 061 — Recent files in Documents

- **Date:** 2026-08-29
- **Commit subject:** List newest files in Documents behind the broker
- **Stage:** Stage 3

## Summary

Testers can ask for the newest files in Documents (not only Downloads). The walk reuses `list_recent`: read-only, depth-capped, broker-gated.

## Changes

- Planner maps “documents” / “docs” in folder goals so recent-files (and Explorer) target `~/Documents`
- Phrases “recent documents” / “newest documents” match the recent-files journey
- Bundled workflow pack `list-recent-documents`
- Copy/move to Documents still uses the existing preview path

## Safety / permissions

- Listing is `read` — broker approval, not hard confirmation
- Does not open, move, or delete matches
- Default cap: depth 2, 20 results (same as Downloads)

## How to verify

```powershell
pytest tests/test_broker_and_planner.py tests/test_workflow_packs.py -k "recent or documents"
arbora --provider echo --goal "recent files in documents"
```
