# 041 — Pytest workflow pack

- **Date:** 2026-08-19
- **Commit subject:** Add a broker-gated pytest workflow for the current directory
- **Stage:** Stage 3

## Summary

Testers can ask Arbora to run the project test suite (`run pytest` / `run tests`) without dropping into a generic PowerShell step. The plan checks that pytest is importable, then runs `python -m pytest` behind the broker.

## Changes

- Planner journey for pytest (read version check, mutate suite run)
- Bundled `workflows/pytest.json`
- CLI / demo example goals
- Tests so `run tests` does not become `Get-Date`

## Safety / permissions

- Version probe is `read`
- Suite run is `mutate` (executes tests, may write `.pytest_cache`) — not destructive, not auto-trusted
- No git commit/push and no `pip install`

## How to verify

```powershell
pytest tests/test_broker_and_planner.py tests/test_workflow_packs.py -k pytest
arbora --provider echo --goal "run pytest"
```
