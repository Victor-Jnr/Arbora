# 123 — Color filters inspect

- **Date:** 2026-10-28
- **Commit subject:** Inspect color filters behind the broker without dumping FilterType
- **Stage:** Stage 3

## Summary

Testers can ask whether color filters are on. Arbora reads ColorFiltering Active only — it does not dump FilterType or write AppsUseLightTheme. High contrast stays `inspect_high_contrast`.

## Changes

- Desktop adapter action `inspect_color_filters`
- Planner journey for “color filters” / “is color filter on”
- Enable / disable / high-contrast phrasing does not use this inspect
- Bundled workflow pack `inspect-color-filters`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not write Active, dump FilterType, or change AppsUseLightTheme
- Output that looks like a theme dump or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_color_filters
arbora --provider echo --goal "color filters"
```
