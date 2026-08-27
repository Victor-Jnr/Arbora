# 049 — Recent files in Downloads

- **Date:** 2026-08-22
- **Commit subject:** List newest files in Downloads behind the broker
- **Stage:** Stage 3

## Summary

Testers can ask Arbora for the newest files in Downloads (or another named folder). The walk is read-only and depth-capped so it cannot recurse a whole drive.

## Changes

- Files adapter action `list_recent` (`path`, `max_depth`, `max_results`)
- Planner journey for “recent files in downloads” / “what did I download”
- Bundled workflow pack `list-recent-downloads`
- Refuses walks under the Windows directory; drive roots use depth 1

## Safety / permissions

- Listing is `read` — no hard confirmation
- Does not open, move, or delete matches
- Default cap: depth 2, 20 results

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k recent
arbora --provider echo --goal "recent files in downloads"
```
