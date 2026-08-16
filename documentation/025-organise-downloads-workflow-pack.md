# 025 — Organise downloads workflow pack

- **Date:** 2026-08-16
- **Commit subject:** Add organise downloads workflow pack with preview and apply steps
- **Stage:** Stage 3

## Summary

A bundled workflow pack now matches alternate organise phrases and produces the preview→apply Downloads filing plan with local undo support.

## Changes

- Added `workflows/organise-downloads.json`
- Tests for pack load, match, and step sequence

## Safety / permissions

- Preview step is read-only; apply is `mutate` and needs approval
- Undo path unchanged (`undo last organise`)

## How to verify

```powershell
arbora --provider echo --goal "organise downloads pack" --yes
pytest tests/test_workflow_packs.py -k organise
```
