# 009 — Packaging and first-run for private testers

- **Date:** 2026-08-08
- **Commit subject:** Add Windows first-run packaging path for private testers
- **Stage:** Stage 2

## Summary

Private testers can install Arbora with one PowerShell script, and the Setup dialog now shows a first-run checklist with fix hints for Memory / Ollama / Playwright.

## Changes

- Added `scripts/first_run.ps1` (venv + editable install + optional Chromium)
- Added `docs/install.md` installer guide
- Extended `setup_status.py` with fix hints and `first_run_checklist()`
- Setup dialog renders the checklist (not only Chromium install)
- Linked install path from CONTRIBUTING / prototype / NEXT

## Safety / permissions

- First-run only installs local packages into `.venv`; no broker bypass
- Chromium install remains explicit and optional (`-SkipChromium`)

## How to verify

```powershell
.\scripts\first_run.ps1 -SkipChromium
pytest
arbora-ui
# Setup → First-run checklist
```
