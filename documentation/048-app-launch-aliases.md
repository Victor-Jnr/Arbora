# 048 — Everyday app launch aliases

- **Date:** 2026-08-21
- **Commit subject:** Resolve Chrome, Edge, and VS Code on launch_app
- **Stage:** Stage 3

## Summary

“Open Chrome” no longer falls through to a guessed Ollama plan. Arbora matches a launch journey, maps friendly names to executables, and uses well-known install paths when those files exist.

## Changes

- Desktop aliases for Chrome, Edge, Firefox, VS Code, Discord, Spotify, Slack, Windows Terminal
- `resolve_launch_target` prefers an existing install path over a bare exe name
- Planner journey for “open/launch/start chrome|edge|vscode|…”
- Explorer and workday goals still win over launch

## Safety / permissions

- Launch and focus are `mutate` — broker approval, not hard confirmation
- Does not drive Playwright or type into the page
- Not auto-trusted

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py -k launch
arbora --provider echo --goal "open chrome"
```
