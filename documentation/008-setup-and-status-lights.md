# 008 — Setup button and connection status lights

- **Date:** 2026-08-07
- **Commit subject:** Add Setup button and connection status lights to desktop UI
- **Stage:** Stage 1

## Summary

The Tkinter UI now shows red/yellow/green connection lights for Memory, Ollama, and Playwright, plus a Setup dialog to install Chromium without leaving the app.

## Changes

- Added `setup_status.py` probes and Chromium installer helper
- Desktop chat: corner Connections panel, Setup + Refresh status controls
- Tests for status probes

## Safety / permissions

- Installer only runs `python -m playwright install chromium` in the current environment
- No broker bypass; setup is local tooling only

## How to verify

```powershell
pytest
arbora-ui
# Connections corner + Setup → Install Chromium
```
