# 030 — Git status workflow pack

- **Date:** 2026-08-18
- **Commit subject:** Add read-only git status workflow pack
- **Stage:** Stage 3

## Summary

A bundled workflow pack adds developer-tool inspection for git: `git status` and `git diff --stat` in the current directory, read-only behind the broker.

## Changes

- Added `workflows/git-status.json`
- Tests for pack load, match, and read-only step shape

## Safety / permissions

- All steps are `read` sensitivity — no commits, pushes, or checkouts
- Terminal commands run through the existing broker gate

## How to verify

```powershell
arbora --provider echo --goal "git status pack" --yes
pytest tests/test_workflow_packs.py -k git_status
```
