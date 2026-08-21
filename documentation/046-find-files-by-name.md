# 046 — Find files by name

- **Date:** 2026-08-21
- **Commit subject:** Add a depth-capped filename search behind the broker
- **Stage:** Stage 3

## Summary

Testers can ask Arbora to find a file by name (or glob) under Downloads or another named folder. The walk is read-only and capped so a search cannot recurse the whole drive.

## Changes

- Files adapter action `search_by_name` (`path`, `pattern`, `max_depth`, `max_results`)
- Planner journey for “find … in downloads” / “search for *.pdf”
- Bundled workflow pack `find-files`
- Refuses walks under the Windows directory; drive roots use depth 1

## Safety / permissions

- Search is `read` — no hard confirmation
- Does not open, move, or delete matches
- Default cap: depth 3, 50 results

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k find
arbora --provider echo --goal "find invoice.pdf in downloads"
```
