# 003 — Trusted routines and local Ollama provider

- **Date:** 2026-08-02
- **Commit subject:** Add trusted-routine reuse and Ollama gpt-oss:20b planning
- **Stage:** Stage 1

## Summary

Trusted routines now re-run matching plans without a fresh approval (hard confirmations still required), and persist across sessions. Unmatched goals can be planned by a local Ollama model (`gpt-oss:20b` by default).

## Changes

- Broker auto-allows scoped non-sensitive steps when a trusted routine fingerprint matches
- Trusted routines persist in local memory and reload on startup
- Added `OllamaProvider` using the local Ollama HTTP API
- Planner uses Ollama JSON plans for unmatched goals, with catalog validation
- CLI: trusted-match skip path, `--provider`, `/provider`
- Tests for trusted reuse, persistence, and provider JSON planning

## Safety / permissions

- Hard-confirmation classes still require an explicit yes inside trusted routines
- Model output cannot invent adapters/actions outside the allow-list
- Broker remains the only path to tool side effects

## How to verify

```powershell
pytest
arbora --provider echo --goal "list files in ~/Downloads" --yes --promote list-dl
arbora --provider echo --goal "list files in ~/Downloads"
ollama list
arbora --provider ollama
```
