# 013 — Journey hardening for priority plans

- **Date:** 2026-08-09
- **Commit subject:** Harden workday, diagnostic, and research journey plans
- **Stage:** Stage 2

## Summary

Priority journey templates now have clearer multi-step rationales, broader phrase matching, and more intentional steps (morning briefing, network probe, briefs folder ensure) while keeping diagnostics read-only.

## Changes

- Workday start/shutdown: ensure folder, briefing/resume notes, expanded matchers
- Diagnostic: disk GB + memory + network probe; still all `read`
- Research: ensure ArboraBriefs, stronger untrusted-data rationale, "look up" phrasing
- Dev setup: safer toolchain check + ArboraProjects folder
- Regression tests for alternate phrasings

## Safety / permissions

- Diagnostic journey remains read-only (no silent repairs)
- Research still treats page text as untrusted data
- Workday does not force-quit apps

## How to verify

```powershell
arbora --provider echo --goal "morning setup" --yes
arbora --provider echo --goal "slow pc low disk" --yes
arbora --provider echo --goal "look up https://example.com" --yes
pytest tests/test_broker_and_planner.py tests/test_browser_adapter.py
```
