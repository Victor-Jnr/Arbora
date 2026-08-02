# Changelog

Per-file roles and one-line change summaries for Arbora. Update this file on every commit (see [CONTRIBUTING.md](CONTRIBUTING.md)).

---

## File roles

| File | Role |
| --- | --- |
| `README.md` | Product vision, safety contract, and project north star |
| `LICENSE` | GPL-3.0 license text |
| `CONTRIBUTING.md` | Contributor setup and product contribution norms |
| `SECURITY.md` | Vulnerability reporting and security expectations |
| `.gitignore` | Ignore venv, caches, local memory, and build artifacts |
| `pyproject.toml` | Package metadata, entrypoint `arbora`, and pytest config |
| `CHANGELOG.md` | Per-file roles and one-line change summaries per commit |
| `documentation/README.md` | Index of numbered commit documents |
| `documentation/001-stage1-prototype-bootstrap.md` | Change doc for Stage 1 prototype bootstrap |
| `documentation/002-commit-documentation-process.md` | Change doc for documentation process + changelog |
| `docs/prototype.md` | How to run and extend the Stage 1 prototype |
| `apps/README.md` | Placeholder for future desktop shell / UI |
| `scripts/demo_journeys.py` | Dry-run smoke demo of priority journeys |
| `src/arbora/__init__.py` | Package version and top-level identity |
| `src/arbora/core/__init__.py` | Core exports (broker, planner, audit, types) |
| `src/arbora/core/types.py` | Shared plan, step, scope, trust, and audit types |
| `src/arbora/core/audit.py` | Append-only in-memory audit log |
| `src/arbora/core/broker.py` | Permission broker — sole gate to tool side effects |
| `src/arbora/core/planner.py` | Rule-based goal → plan stub for priority journeys |
| `src/arbora/adapters/__init__.py` | Adapter package exports |
| `src/arbora/adapters/desktop.py` | Windows app list/launch adapter |
| `src/arbora/adapters/files.py` | Files/folders listing, write, organise preview |
| `src/arbora/adapters/terminal.py` | PowerShell execution adapter |
| `src/arbora/memory/__init__.py` | Memory package exports |
| `src/arbora/memory/store.py` | Local on-device preferences key/value store |
| `src/arbora/providers/__init__.py` | Provider package exports |
| `src/arbora/providers/base.py` | Provider-agnostic model protocol |
| `src/arbora/providers/echo.py` | Local stub provider (no network) |
| `src/arbora/cli/__init__.py` | CLI package marker |
| `src/arbora/cli/session.py` | Runtime wiring and plan formatting helpers |
| `src/arbora/cli/main.py` | Interactive and one-shot CLI chat shell |
| `tests/test_broker_and_planner.py` | Broker, planner, trust, and memory regression tests |

---

## 002 — Commit documentation process (2026-08-02)

| File | Change |
| --- | --- |
| `CHANGELOG.md` | Extended file-role table and added section 002 one-liners |
| `documentation/002-commit-documentation-process.md` | Recorded documentation/changelog process |
| `documentation/README.md` | Indexed document 002 and linked CHANGELOG |
| `README.md` | Documented commit-doc process and latest docs |
| `CONTRIBUTING.md` | Added commit documentation and changelog duty |

---

## 001 — Stage 1 prototype bootstrap (2026-08-02)

| File | Change |
| --- | --- |
| `LICENSE` | Added full GPL-3.0 license text |
| `CONTRIBUTING.md` | Added setup, high-value areas, and safety norms |
| `SECURITY.md` | Added private reporting path and hard-confirmation classes |
| `.gitignore` | Added Python, venv, pytest, and `.arbora/` ignores |
| `pyproject.toml` | Added editable package, `arbora` script, and pytest paths |
| `README.md` | Marked Stage 1 prototype status and install pointers |
| `CHANGELOG.md` | Started file-role table and per-file one-line change summaries |
| `docs/prototype.md` | Added run instructions and Stage 1 design invariants |
| `apps/README.md` | Noted CLI-first Stage 1; desktop UI deferred |
| `scripts/demo_journeys.py` | Added dry-run demo for workday/diagnose/dev/organise |
| `src/arbora/__init__.py` | Set package version `0.1.0a0` |
| `src/arbora/core/types.py` | Defined Plan, ToolStep, scopes, trust, and sensitivities |
| `src/arbora/core/audit.py` | Implemented in-memory audit event log |
| `src/arbora/core/broker.py` | Implemented authorize/execute with hard confirmations |
| `src/arbora/core/planner.py` | Added rule-based plans for priority journeys |
| `src/arbora/core/__init__.py` | Exported core public symbols |
| `src/arbora/adapters/desktop.py` | Added list/launch Windows apps via PowerShell |
| `src/arbora/adapters/files.py` | Added list/ensure/write/preview-organise actions |
| `src/arbora/adapters/terminal.py` | Added scoped PowerShell runner with dry-run |
| `src/arbora/adapters/__init__.py` | Exported desktop, files, and terminal adapters |
| `src/arbora/memory/store.py` | Added local JSON preference store with wipe |
| `src/arbora/memory/__init__.py` | Exported `LocalMemoryStore` |
| `src/arbora/providers/base.py` | Defined `ModelProvider` protocol |
| `src/arbora/providers/echo.py` | Added deterministic local echo stub |
| `src/arbora/providers/__init__.py` | Exported provider symbols |
| `src/arbora/cli/session.py` | Wired runtime and approve helpers |
| `src/arbora/cli/main.py` | Added interactive plan→approve→execute shell |
| `src/arbora/cli/__init__.py` | Added CLI package |
| `tests/test_broker_and_planner.py` | Added eight safety/planner regression tests |
| `documentation/001-stage1-prototype-bootstrap.md` | Recorded Stage 1 bootstrap change document |
| `documentation/README.md` | Started numbered documentation index with 001 |
