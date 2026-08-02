# 001 — Stage 1 prototype bootstrap

- **Date:** 2026-08-02
- **Commit subject:** Bootstrap Stage 1 prototype with broker, adapters, and CLI
- **Stage:** Stage 1

## Summary

Moved Arbora from vision-only into a runnable Stage 1 prototype: permission broker as the sole gate to side effects, rule-based planner for priority journeys, Windows adapters, and an interactive CLI chat loop.

## Changes

- Added GPL-3.0 `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, and `.gitignore`
- Python package under `src/arbora/` (`core`, `adapters`, `memory`, `providers`, `cli`)
- Permission broker with hard confirmations for destructive / credential / financial steps
- Adapters: desktop, files, terminal (dry-run supported)
- Rule-based `GoalPlanner` for workday, diagnostics, and developer setup
- CLI entrypoint `arbora` with plan → approve → execute and `/audit`, `/routines`, `/revoke`
- Tests under `tests/`; demo script `scripts/demo_journeys.py`
- Prototype notes in `docs/prototype.md`
- Started `CHANGELOG.md` with file roles and per-file one-line summaries
- Recorded this commit as `documentation/001-…`

## Safety / permissions

- Models propose; only the broker may invoke adapters
- Hard-confirmation classes cannot be silently auto-approved
- CLI defaults to dry-run (`/dry off` or `--execute` for live runs)

## How to verify

```powershell
pip install -e ".[dev]"
pytest
arbora --goal "diagnose disk space" --yes
```
