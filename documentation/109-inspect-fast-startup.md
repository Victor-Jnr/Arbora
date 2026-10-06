# 109 — Fast startup inspect

- **Date:** 2026-10-06
- **Commit subject:** Inspect fast startup behind the broker without changing hibernation
- **Stage:** Stage 3

## Summary

Testers can ask whether Windows fast startup is on. Arbora reads HiberbootEnabled only — it does not dump HibernateEnabled or run `powercfg /h`. Startup apps stay `inspect_startup`.

## Changes

- Desktop adapter action `inspect_fast_startup`
- Planner journey for “fast startup” / “hiberboot” / “is fast startup on”
- Enable / disable / turn on / turn off phrasing does not use this inspect
- Bundled workflow pack `inspect-fast-startup`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not read HibernateEnabled, run powercfg /h, or write HiberbootEnabled
- Output that looks like a hibernation dump or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_fast_startup
arbora --provider echo --goal "fast startup"
```
