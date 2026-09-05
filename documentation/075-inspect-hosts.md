# 075 — Hosts file inspect

- **Date:** 2026-09-05
- **Commit subject:** Inspect the hosts file behind the broker without editing it
- **Stage:** Stage 3

## Summary

Testers can ask what is in the Windows hosts file and get a capped read-only list of IP-to-name mappings. Comments are counted, not dumped. Arbora does not edit the file.

## Changes

- Desktop adapter action `inspect_hosts` (fixed System32 hosts path; caller `path` args ignored)
- Planner journey for “hosts file” / “what's in hosts”
- Edit/add/remove phrasing does not use this inspect
- Bundled workflow pack `inspect-hosts`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the read and does not open the file
- Does not call Set-Content, Add-Content, or notepad
- Output that looks like a password or key is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k hosts
arbora --provider echo --goal "hosts file"
```
