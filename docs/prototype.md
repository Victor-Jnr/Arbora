# Stage 1 prototype notes

## What exists

- Python package under `src/arbora/`
- Permission broker (`core/broker.py`) as the only path to tool side effects
- Rule-based goal planner for priority journeys, with local Ollama fallback for unmatched goals
- Trusted routines: matching plans skip re-approval (hard confirmations still required)
- Windows adapters: desktop, files, terminal, browser (Playwright)
- Local memory with Fernet encryption at rest (Windows DPAPI-wrapped key)
- Providers: Ollama (`gpt-oss:20b` by default) and echo stub
- Interactive CLI chat: plan → approve → execute (`arbora`)
- Desktop chat UI: Tkinter (`arbora-ui`)

## Run

Private testers (recommended):

```powershell
.\scripts\first_run.ps1
.\.venv\Scripts\Activate.ps1
arbora-ui
```

See [install.md](install.md) for details. Manual path:

```powershell
pip install -e ".[dev]"
playwright install chromium
arbora
```

Uses local Ollama by default (`ARBORA_PROVIDER=ollama`, model `gpt-oss:20b`).
Ensure `ollama serve` is running and the model is pulled:

```powershell
ollama pull gpt-oss:20b
```

Force the offline stub:

```powershell
arbora --provider echo
```

Non-interactive dry-run demo:

```powershell
arbora --goal "diagnose disk space" --yes
arbora --goal "start my workday" --yes --promote workday
arbora --goal "start my workday"
```

The third call should match the trusted routine and run without `--yes`.

Live execution: add `--execute`. Hard-confirmation steps still need `--hard-yes`.

Research dry-run:

```powershell
arbora --provider echo --goal "research https://example.com" --yes
arbora-ui
```

## Design invariants

1. Models propose; the broker disposes.
2. Adapters never run unless the broker authorises the step.
3. Destructive / credential / financial steps always need hard confirmation — even inside trusted routines.
4. Dry-run is the default in the CLI.
5. Personal memory is encrypted at rest locally (`/memory`, `/wipe`).
6. Browser page text is untrusted data and is never auto-executed as tools.

## Next spikes

Near-term build order lives in **[NEXT.md](NEXT.md)** (source of truth). Current top plates:

- ~~Packaging + first-run for private testers~~ (done — see `scripts/first_run.ps1`)
- `arbora doctor` + trust UX (revoke / audit / emergency stop)
- Journey hardening and richer broker-gated browser actions
