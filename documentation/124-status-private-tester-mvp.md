# 124 — Private-tester MVP status honesty

- **Date:** 2026-10-29
- **Commit subject:** Tell testers Arbora is a private-tester MVP, not a vision-only README
- **Stage:** Stage 3

## Summary

Testers reading the README now see a private-tester MVP (venv first-run, no signed installer) instead of a vision-only Stage 1 prototype. Stage 2 capability plates stay marked done; Stage 3 continues.

## Changes

- README status badge, project-status table, roadmap labels, layout, and glossary
- CLI banner and package docstring
- CONTRIBUTING intro
- `docs/NEXT.md` current position and P37 plate 112
- `docs/prototype.md` title and next-spikes pointer

## Safety / permissions

- None — documentation and banner wording only

## How to verify

```powershell
git grep -n "Vision stage" README.md docs/prototype.md CONTRIBUTING.md src/arbora/cli/main.py
arbora --help
```
