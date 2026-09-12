# 084 — Localhost plan-accept HTTP API

- **Date:** 2026-09-12
- **Commit subject:** Add a localhost HTTP API that accepts plans through the broker
- **Stage:** Stage 3

## Summary

API callers can create a plan with `POST /v1/goals`, then explicitly accept steps with `POST /v1/plans/{id}/approve`. The server binds loopback only, requires a token, defaults to dry-run, and still needs `hard_confirm` for hard-confirmation classes. `auto_approve` is rejected.

## Changes

- Package `arbora.api` with token-gated request dispatcher
- CLI `arbora serve` (host must be 127.0.0.1 / localhost / ::1)
- `GET /v1/health` reuses doctor JSON; audit and routine list/revoke endpoints
- Tests for missing token, auto_approve refusal, accept_all_non_hard, and hard steps

## Safety / permissions

- Adapters still run only through the permission broker
- Dry-run is the default; live requires `dry_run: false` on create or approve
- Hard-confirmation classes cannot be accepted without `hard_confirm`
- Bind address is loopback-only; wildcard hosts are refused
- Token via `--token`, `ARBORA_API_TOKEN`, or a one-time generated value

## How to verify

```powershell
pytest tests/test_api_accept.py tests/test_doctor.py
arbora serve --provider echo --token arbora-test-token-1
```
