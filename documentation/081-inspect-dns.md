# 081 — DNS servers inspect

- **Date:** 2026-09-11
- **Commit subject:** Inspect DNS servers behind the broker without changing them
- **Stage:** Stage 3

## Summary

Testers can ask which IPv4 DNS servers this PC uses. Arbora returns a capped per-interface list — it does not change DNS, flush the cache, or return Wi-Fi keys.

## Changes

- Desktop adapter action `inspect_dns`
- Planner journey for “dns servers” / “what's my dns” / “name servers”
- Change / flush phrasing does not use this inspect; wifi status and IP stay on `inspect_network`
- Bundled workflow pack `inspect-dns`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not call Set-DnsClientServerAddress or Clear-DnsClientCache
- Output that looks like a password or key is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k dns
arbora --provider echo --goal "dns servers"
```
