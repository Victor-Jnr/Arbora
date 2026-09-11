# 079 — Firewall profile inspect

- **Date:** 2026-09-11
- **Commit subject:** Inspect Windows Firewall profiles behind the broker without changing them
- **Stage:** Stage 3

## Summary

Testers can ask whether Windows Firewall is on. Arbora returns Domain, Private, and Public profile Enabled flags only — not a rule dump, and it does not enable or disable the firewall.

## Changes

- Desktop adapter action `inspect_firewall`
- Planner journey for “firewall” / “is the firewall on” / “windows firewall”
- Disable / turn off / enable phrasing does not use this inspect
- Bundled workflow pack `inspect-firewall`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not call Get-NetFirewallRule, Set-NetFirewallProfile, or New-NetFirewallRule
- Output that looks like a password, key, or rule dump is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k firewall
arbora --provider echo --goal "firewall"
```
