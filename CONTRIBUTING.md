# Contributing to Arbora

Thanks for your interest. Arbora is early (Stage 1 prototype). The [README](README.md) is still the north star for product intent and the safety contract.

## Git workflow

Do not commit on `main`. Treat it as the last known-good line testers clone.

| Branch | Role |
| --- | --- |
| `main` | Default. Update only by pull request after **pytest (Windows)** is green. |
| `dev` | Optional integration branch. Create it when you want a staging line. |
| `feature/…`, `fix/…` | One change per branch. Open a PR into `main` (or into `dev` if that branch exists). |

Typical day:

```powershell
git checkout main
git pull origin main
git checkout -b feature/short-name
# …edit, pytest, commit…
git push -u origin HEAD
```

Then open a pull request with **base = `main`**. Wait for GitHub Actions **pytest (Windows)** (pytest + `arbora validate`). Merge only when that check is green.

### Require the check on GitHub (one-time)

The workflow file is not enough by itself: GitHub will still merge a red PR unless the branch is protected.

1. Merge a PR that contains `.github/workflows/ci.yml` so the workflow exists on `main`.
2. GitHub → **Settings** → **Branches** → **Add branch protection rule** (or **Rulesets**) for `main`.
3. Enable **Require status checks to pass before merging**.
4. Require the check named **`pytest (Windows)`**.
5. Enable **Require branches to be up to date before merging**.
6. Do **not** require a second approving review unless you have another reviewer.

Until that rule exists, treat a red **pytest (Windows)** check as a merge blocker even if GitHub still allows the button.

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
