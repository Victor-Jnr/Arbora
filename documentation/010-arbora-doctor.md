# 010 — arbora doctor CLI

- **Date:** 2026-08-08
- **Commit subject:** Add arbora doctor health checks with fix hints
- **Stage:** Stage 2

## Summary

`arbora doctor` probes Memory, Ollama, and Playwright using the same helpers as Setup, prints fix hints, and exits non-zero when checks are yellow or red.

## Changes

- Added `src/arbora/cli/doctor.py`
- `arbora doctor` / `arbora doctor --json` dispatch from CLI main
- Tests for exit codes and output
- Documented in install / prototype / NEXT

## Safety / permissions

- Read-only probes only; no tool execution or broker bypass

## How to verify

```powershell
arbora doctor
arbora doctor --json
pytest tests/test_doctor.py
```
