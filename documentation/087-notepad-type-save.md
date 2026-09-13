# 087 — Notepad type and named save

- **Date:** 2026-09-13
- **Commit subject:** Type into Notepad then write a named notes file
- **Stage:** Stage 3

## Summary

Testers can open Notepad, type approved text after a foreground check, and save a named `.txt` into the notes folder. The named file is written with `files.write_text`, not a Save As dialog. Failed launch, focus, type, or write steps halt the rest of the plan.

## Changes

- Planner extends the type-in-window journey when the goal includes “save as …” / “save to …”
- Filename is a basename-only `.txt` (illegal path characters and `..` stripped)
- Bundled workflow pack `type-in-notepad`

## Safety / permissions

- Steps are `mutate` — broker approval, not hard confirmation
- Same typing rules as `type_in_window` (no SendKeys; secrets refused)
- Does not steal “save a note about …”
- Path is always under the notes folder; Windows/absolute prefixes are dropped

## How to verify

```powershell
pytest tests/test_broker_and_planner.py tests/test_workflow_packs.py -k "notepad_type or type_in_notepad"
arbora --provider echo --goal "type hello in notepad and save as hello.txt"
```
