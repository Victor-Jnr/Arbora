# 083 — Pending reboot inspect

- **Date:** 2026-09-12
- **Commit subject:** Inspect pending reboot flags behind the broker without restarting
- **Stage:** Stage 3

## Summary

Testers can ask whether this PC needs a restart. Arbora reads Windows Update, Component Based Servicing, and pending-file-rename flags only — it does not restart or shut down.

## Changes

- Desktop adapter action `inspect_pending_reboot`
- Planner journey for “pending reboot” / “does this pc need a restart” / “is a restart pending”
- Restart-now / shutdown phrasing does not use this inspect; uptime stays on `inspect_uptime`
- Bundled workflow pack `inspect-pending-reboot`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not call Restart-Computer, Stop-Computer, or shutdown
- Output that looks like a password or key is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k pending_reboot
arbora --provider echo --goal "pending reboot"
```
