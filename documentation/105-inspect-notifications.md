# 105 — Notification toasts inspect

- **Date:** 2026-10-04
- **Commit subject:** Inspect notification toasts behind the broker without dumping history
- **Stage:** Stage 3

## Summary

Testers can ask whether Windows notification toasts are on. Arbora reads ToastEnabled only — it does not dump notification history or Focus Assist. Camera / microphone / location stay their own inspects.

## Changes

- Desktop adapter action `inspect_notifications`
- Planner journey for “notifications” / “are notifications on” / “notification toasts”
- Enable / disable / clear / Focus Assist phrasing does not use this inspect
- Bundled workflow pack `inspect-notifications`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not call Get-ChildItem, dump toast XML, or read Focus Assist CloudStore
- Output that looks like notification history or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_notifications
arbora --provider echo --goal "are notifications on"
```
