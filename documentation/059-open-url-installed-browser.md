# 059 — Open URL in installed Chrome/Edge

- **Date:** 2026-08-28
- **Commit subject:** Open an http(s) URL in installed Chrome or Edge behind the broker
- **Stage:** Stage 3

## Summary

Testers can ask to open an http(s) URL in installed Chrome, Edge, or Firefox. Arbora uses `Start-Process` on the same launch targets as `launch_app`. It does not start Playwright. File, javascript, ftp, and credential-bearing URLs are refused.

## Changes

- Desktop adapter action `open_in_browser` (`url`, `name`)
- Planner journey for “open https://example.com in chrome”
- Research journeys still use the Playwright browser adapter
- Bundled workflow pack `open-url-installed-browser`

## Safety / permissions

- Open is `mutate` — broker approval, not hard confirmation
- Dry-run names the browser and URL and does not start a process
- Only `http` / `https` with a host; no embedded credentials
- Does not pass extra browser flags

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k "open_in_browser or open_url"
arbora --provider echo --goal "open https://example.com in chrome"
```
