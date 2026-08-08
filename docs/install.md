# Install Arbora (private testers)

Windows-first install path for early testers. This is not a signed end-user installer yet; it is the supported way to get a working local build without improvising `pip` steps.

## Requirements

- Windows 10/11
- Python **3.11+** on `PATH` (`py` launcher or `python`)
- Optional: [Ollama](https://ollama.com/) for local planning models
- Optional: network access once for Playwright Chromium

## One-shot first run

From the repo root in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\first_run.ps1
```

Skip browser runtime (faster):

```powershell
.\scripts\first_run.ps1 -SkipChromium
```

The script:

1. creates `.venv` if missing;
2. installs Arbora editable with dev extras (`pip install -e ".[dev]"`);
3. installs Playwright Chromium unless `-SkipChromium`;
4. prints how to launch `arbora` / `arbora-ui`.

Then:

```powershell
.\.venv\Scripts\Activate.ps1
arbora-ui
```

Open **Setup** in the UI to review the first-run checklist (Memory / Ollama / Playwright) and install Chromium if you skipped it.

## Manual path (same outcome)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
playwright install chromium
arbora --help
arbora-ui
```

## Local model (optional)

```powershell
ollama pull gpt-oss:20b
```

Echo provider works offline for dry-run demos:

```powershell
arbora --provider echo --goal "diagnose disk space" --yes
```

## Verify

```powershell
pytest
```

Connection lights in `arbora-ui` should show Memory green. Ollama and Playwright may be yellow/red until you complete those optional steps.

## What this is not

- Not a Microsoft Store / MSI product yet
- Not a cloud-hosted service
- Does not grant Arbora unsupervised system control — plan → approve → execute still applies

More prototype notes: [prototype.md](prototype.md). Near-term build order: [NEXT.md](NEXT.md).
