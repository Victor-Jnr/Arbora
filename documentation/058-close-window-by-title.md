# 058 — Close window by title

- **Date:** 2026-08-28
- **Commit subject:** Close a titled window with WM_CLOSE behind the broker
- **Stage:** Stage 3

## Summary

Testers can ask to close a window by title. Arbora sends WM_CLOSE (`CloseMainWindow`) to the first matching visible window. It does not force-kill with `taskkill` or `Stop-Process`. Broker approval is still required; this is mutate, not destructive.

## Changes

- Desktop adapter action `close_window` (`title_contains` / `name`)
- Planner journey for “close the notepad window” / “close window titled …”
- Workday shutdown still only lists apps and does not auto-close
- Bundled workflow pack `close-window`

## Safety / permissions

- Close is `mutate` — broker approval, not hard confirmation
- Dry-run describes WM_CLOSE and does not touch windows
- Script is refused if it looks like taskkill / Stop-Process / Kill
- Does not close untitled/unnamed processes; first title match only

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k "close_window"
arbora --provider echo --goal "close the notepad window"
```
