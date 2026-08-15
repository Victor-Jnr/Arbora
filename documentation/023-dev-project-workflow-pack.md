# 023 — Developer project workflow pack

- **Date:** 2026-08-15
- **Commit subject:** Add developer project scaffold pack and hardened setup journey
- **Stage:** Stage 3

## Summary

MVP journey #3 (developer project setup) now scaffolds starter `README.md` and `.gitignore` files after toolchain inspection. A bundled workflow pack adds alternate goal phrases for the same scaffold flow.

## Changes

- Added `workflows/dev-project-setup.json` workflow pack
- Hardened built-in `set up a project` journey with scaffold write steps
- Extended workflow pack tests for match and live scaffold dry-run/execute

## Safety / permissions

- Scaffold writes are `mutate` sensitivity — still require user approval
- No auto-run install/clone/venv commands
- Broker gate unchanged

## How to verify

```powershell
arbora --provider echo --goal "set up a project" --yes --execute
arbora --provider echo --goal "dev project pack" --yes
pytest tests/test_workflow_packs.py -k dev
```
