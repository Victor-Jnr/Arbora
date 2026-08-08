# Contributing to Arbora

Thanks for your interest. Arbora is early (Stage 1 prototype). The [README](README.md) is still the north star for product intent and the safety contract.

## Before you change code

1. Read the [safety contract](README.md#safety-contract) and [autonomy model](README.md#autonomy-and-permissions).
2. Do **not** add tool capabilities that bypass the permission broker.
3. Prefer small, reviewable changes. Call out safety implications in the PR description.
4. Discuss large architectural changes before implementing them.

## Development setup

Preferred private-tester path on Windows:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\first_run.ps1
.\.venv\Scripts\Activate.ps1
pytest
arbora --help
```

Full guide: [docs/install.md](docs/install.md).

Manual equivalent:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
arbora --help
```

## High-value areas

- Permission broker / policy engine and safety regression tests
- Windows adapters that stay least-privilege
- Plan / approval / audit UX
- Provider adapters (local runtimes and opt-in cloud APIs)
- Local memory encryption and wipe/export flows

## Norms

- No secrets, personal traces, or live credentials in commits
- Document intent vs. availability carefully — vision ≠ shipped feature
- New mutating adapters need dry-run support and audit coverage
- Hard-confirmation classes (financial, credential, destructive) must never be silently auto-approved
- Keep [`CHANGELOG.md`](CHANGELOG.md) and [`documentation/`](documentation/README.md) in sync with product changes

Issue templates and a code of conduct will expand as the project matures.
