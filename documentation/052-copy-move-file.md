# 052 — Copy or move a file with preview

- **Date:** 2026-08-24
- **Commit subject:** Preview then copy or move a file behind the broker
- **Stage:** Stage 3

## Summary

Testers can ask Arbora to copy or move one file after a read-only preview. Overwrite is refused. Moves record an undo batch in the existing organise journal.

## Changes

- Files adapter actions `preview_copy_move`, `copy_file`, and `move_file`
- Planner journey for “copy/move the file X to documents”
- Bundled workflow pack `copy-file`
- “undo last move” reuses `undo_last_organise`

## Safety / permissions

- Preview is `read`; copy/move are `mutate` — broker approval, not hard confirmation
- Dry-run prints the paths and does not touch files
- Refuses the Windows directory and existing destinations
- Copy is not auto-undone (that would delete the new file)

## How to verify

```powershell
pytest tests/test_file_undo.py tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k "copy or move"
arbora --provider echo --goal "copy the file report.pdf to documents"
```
