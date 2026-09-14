# 088 — Sandbox auto-execute HTTP

- **Date:** 2026-09-14
- **Commit subject:** Add opt-in sandbox one-shot execute on the localhost API
- **Stage:** Stage 3

## Summary

Isolated hosts can start `arbora serve --sandbox-auto-execute` and call `POST /v1/execute` so a local caller plans and runs non-hard steps in one request. The flag is off by default. Loopback, token, dry-run default, and hard confirmation are unchanged. Operator guide: [docs/sandbox.md](../docs/sandbox.md).

## Changes

- `POST /v1/execute` when `ApiSession.sandbox_auto_execute` is true
- CLI `--sandbox-auto-execute` and env `ARBORA_SANDBOX_AUTO_EXECUTE`
- `GET /v1/health` reports `sandbox_auto_execute`
- Official operator guide `docs/sandbox.md`

## Safety / permissions

- Default `arbora serve` still returns 403 on `/v1/execute`
- `auto_approve` remains rejected on `/v1/goals` and `/v1/execute`
- Dry-run still defaults to true
- Hard classes still need `hard_confirm`
- Bind remains loopback-only
- Broker still authorises every adapter call

## How to verify

```powershell
pytest tests/test_api_accept.py -q
arbora serve --provider echo --token arbora-test-token-1 --sandbox-auto-execute
```

See [docs/sandbox.md](../docs/sandbox.md) for health check and `POST /v1/execute` examples.
