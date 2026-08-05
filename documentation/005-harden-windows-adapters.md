# 005 — Harden Windows adapters

- **Date:** 2026-08-05
- **Commit subject:** Harden Windows desktop, files, and terminal adapters
- **Stage:** Stage 1

## Summary

Shared PowerShell runner with timeouts/truncation, clearer path and permission errors, app launch aliases, and window focus support — without bypassing the permission broker.

## Changes

- Added `adapters/powershell.py` shared runner (`-NonInteractive`, UTF-8, timeout, truncation)
- Desktop: app aliases, clearer launch errors, `focus_window`
- Files: `~`/env expansion, PermissionError/OSError handling
- Terminal: uses shared runner; surfaces timeouts cleanly
- Workday plan focuses Notepad after launch
- Adapter hardening tests

## Safety / permissions

- New actions remain broker-gated; `focus_window` is mutate-class
- Hard-confirmation classes unchanged

## How to verify

```powershell
pytest
arbora --provider echo --goal "start my workday" --yes
arbora --provider echo --goal "list files in ~/Downloads" --yes --execute
```
