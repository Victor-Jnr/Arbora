# 015 — File undo for organise moves

- **Date:** 2026-08-12
- **Commit subject:** Add undo for organise file moves with local journal
- **Stage:** Stage 2

## Summary

Downloads organisation can now apply extension-based moves and record an undo batch in encrypted local memory. Users can reverse the last batch via an undo plan or `/undo` in the CLI.

## Changes

- Files adapter: `apply_organise`, `undo_last_organise`, shared move planner
- Undo journal persisted under `file_undo_batches` in local memory
- Organise journey includes apply step; new undo journey matcher
- CLI `/undo` shortcut
- Tests for apply/undo roundtrip

## Safety / permissions

- Moves still require broker approval (mutate sensitivity)
- Undo only reverses recorded batches; no silent auto-undo
- Stops on conflicts (destination already exists)

## How to verify

```powershell
pytest tests/test_file_undo.py
arbora --provider echo --goal "organise my downloads" --yes --execute
arbora --provider echo --goal "undo last organise" --yes --execute
```
