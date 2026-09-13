# 086 — Type into a titled window

- **Date:** 2026-09-13
- **Commit subject:** Type into a titled window after verifying it is foreground
- **Stage:** Stage 3

## Summary

Testers can ask Arbora to type into a matching window (usually Notepad). The adapter focuses that window, checks `GetForegroundWindow`, then sets Document/Edit text with UI Automation or `WM_SETTEXT`. It does not inject global SendKeys. Failed launch/focus/type steps halt the rest of the plan.

## Changes

- Desktop adapter action `type_in_window` (`title_contains`, `text`)
- Planner journey for “type hello in notepad” / “open notepad and type …”
- Bundled workflow pack `type-in-window`

## Safety / permissions

- Typing is `mutate` — broker approval, not hard confirmation
- Dry-run reports character count and a short preview; it does not touch windows
- Secret-like text and payloads over 4000 characters are refused
- If the needle is `notepad`, only process `notepad` is matched (not Notepad++)
- Foreground hwnd must match the target or the step fails
- `halt_on_failure` is set on launch, focus, and type

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k "type_in_window"
arbora --provider echo --goal "type hello in notepad"
```
