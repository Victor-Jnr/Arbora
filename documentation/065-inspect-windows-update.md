# 065 — Windows Update last-install date

- **Date:** 2026-08-31
- **Commit subject:** Inspect the last Windows Update install date behind the broker
- **Stage:** Stage 3

## Summary

Testers can ask when Windows last installed an update and get a read-only last Get-HotFix date and KB. Arbora does not install, download, or scan for updates, and does not dump the full hotfix list.

## Changes

- Desktop adapter action `inspect_windows_update`
- Planner journey for “windows update” / “when were updates installed”
- Install/download/check-for-update phrasing does not use this inspect
- Bundled workflow pack `inspect-windows-update`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call Get-HotFix
- InstalledBy (account names) is not requested
- Full hotfix listing is withheld (count only)

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k windows_update
arbora --provider echo --goal "windows update"
```
