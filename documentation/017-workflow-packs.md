# 017 — Reusable workflow packs

- **Date:** 2026-08-12
- **Commit subject:** Add reusable workflow packs loadable into plans
- **Stage:** Stage 2

## Summary

Arbora now ships JSON workflow packs (bundled + `~/.arbora/workflows/`) that match goal phrases and materialize inspectable plans promotable to trusted routines.

## Changes

- Added `src/arbora/workflows/packs.py` loader/matcher
- Bundled packs: `workflows/list-downloads.json`, `disk-diagnose.json`, `research-example.json`
- Planner uses packs after built-in journeys, before model fallback
- CLI `/workflows` lists available packs
- Tests for load, match, override, and dry-run execution

## Safety / permissions

- Packs only use actions in `ALLOWED_ACTIONS`
- Broker approval and promotion rules unchanged
- User packs override bundled packs by `id`

## How to verify

```powershell
arbora --provider echo
/workflows
# goal: list downloads
pytest tests/test_workflow_packs.py
```
