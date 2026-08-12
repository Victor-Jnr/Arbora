# 016 — Opt-in OpenAI-compatible cloud provider

- **Date:** 2026-08-12
- **Commit subject:** Add opt-in OpenAI-compatible cloud provider with privacy banner
- **Stage:** Stage 2

## Summary

Arbora now supports an explicit opt-in cloud planner provider behind the same interface as Ollama/echo. When selected, CLI and desktop UI show a clear privacy notice that prompt data leaves the machine.

## Changes

- Added `OpenAICompatibleProvider` (`ARBORA_OPENAI_API_KEY`, optional base URL/model)
- `select_provider("openai")`, `list_provider_choices()`, `provider_privacy_notice()`
- Desktop UI: openai in provider list when configured + red privacy banner
- CLI `/provider` and startup banner show privacy notice for cloud
- Tests with mocked HTTP

## Safety / permissions

- Cloud is opt-in only (requires API key; not default)
- No automatic exfiltration of local memory or audit logs — only planner prompts
- Broker/adapter behaviour unchanged

## How to verify

```powershell
$env:ARBORA_OPENAI_API_KEY = "sk-..."
arbora --provider openai --goal "list files in ~/Downloads" --yes
pytest tests/test_openai_provider.py
arbora-ui  # select openai when key is set; banner appears
```
