# Stage 1 prototype notes

## What exists

- Python package under `src/arbora/`
- Permission broker (`core/broker.py`) as the only path to tool side effects
- Rule-based goal planner stub (`core/planner.py`) for the three priority journeys
- Windows adapters: desktop, files, terminal
- Local memory sketch (`memory/store.py`)
- Echo local model provider stub
- Interactive CLI chat: plan → approve → execute (`arbora`)

## Run

```powershell
pip install -e ".[dev]"
arbora
```

Non-interactive dry-run demo:

```powershell
arbora --goal "diagnose disk space" --yes
arbora --goal "start my workday" --yes
arbora --goal "set up a project" --yes
```

Live execution (leave dry-run): add `--execute`. Hard-confirmation steps still need `--hard-yes`.

## Design invariants

1. Models propose; the broker disposes.
2. Adapters never run unless the broker authorises the step.
3. Destructive / credential / financial steps always need hard confirmation.
4. Dry-run is the default in the CLI.

## Next spikes

- Desktop chat UI (`apps/`)
- Real local/cloud model providers behind `providers/`
- Fernet (or OS keychain) encryption for `memory/`
- Trusted-routine matching on subsequent identical goals without re-prompting every step
- Browser adapter
