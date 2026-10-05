# 106 — Remote Desktop inspect

- **Date:** 2026-10-05
- **Commit subject:** Inspect Remote Desktop behind the broker without dumping RDP ports
- **Stage:** Stage 3

## Summary

Testers can ask whether Remote Desktop is on. Arbora reads fDenyTSConnections only — it does not dump listening ports or enable Terminal Services. This is a local inspect, not remote desktop control.

## Changes

- Desktop adapter action `inspect_remote_desktop`
- Planner journey for “remote desktop” / “is rdp on” / “is remote desktop enabled”
- Enable / disable / turn on / turn off phrasing does not use this inspect
- Bundled workflow pack `inspect-remote-desktop`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not read PortNumber, dump 3389, or write fDenyTSConnections
- Output that looks like a port dump or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_remote_desktop
arbora --provider echo --goal "remote desktop"
```
