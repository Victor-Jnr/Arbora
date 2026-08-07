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
| `documentation/003-trusted-routines-and-ollama.md` | Change doc for trusted routines and Ollama provider |
| `documentation/004-encrypted-local-memory.md` | Change doc for encrypted local memory |
| `documentation/005-harden-windows-adapters.md` | Change doc for Windows adapter hardening |
| `documentation/006-browser-adapter-playwright.md` | Change doc for Playwright browser adapter |
| `documentation/007-tkinter-desktop-chat.md` | Change doc for Tkinter desktop chat |
| `docs/prototype.md` | How to run and extend the Stage 1 prototype |
| `apps/README.md` | Desktop chat run instructions |
| `apps/__init__.py` | Apps package marker |
| `apps/desktop_chat/__init__.py` | Desktop chat package marker |
| `apps/desktop_chat/__main__.py` | `python -m apps.desktop_chat` entry |
| `apps/desktop_chat/app.py` | Tkinter plan→approve→execute chat window |
| `scripts/demo_journeys.py` | Dry-run smoke demo of priority journeys |
| `src/arbora/__init__.py` | Package version and top-level identity |
| `src/arbora/core/__init__.py` | Core exports (broker, planner, audit, types) |
| `src/arbora/core/types.py` | Shared plan, step, scope, trust, and audit types |
| `src/arbora/core/audit.py` | Append-only in-memory audit log |
| `src/arbora/core/broker.py` | Permission broker — sole gate to tool side effects |
| `src/arbora/core/planner.py` | Goal → plan via templates and optional local model |
| `src/arbora/core/routines_store.py` | Serialize/load trusted routines for local memory |
| `src/arbora/adapters/__init__.py` | Adapter package exports |
| `src/arbora/adapters/powershell.py` | Shared PowerShell runner with timeout/truncation |
| `src/arbora/adapters/desktop.py` | Windows app list/launch/focus adapter |
| `src/arbora/adapters/files.py` | Files/folders listing, write, organise preview |
| `src/arbora/adapters/terminal.py` | PowerShell execution adapter |
| `src/arbora/adapters/browser.py` | Playwright browser navigate/extract/brief adapter |
| `src/arbora/memory/__init__.py` | Memory package exports |
| `src/arbora/memory/crypto.py` | Fernet encryption and DPAPI/file key wrapping |
| `src/arbora/memory/store.py` | Encrypted on-device preferences key/value store |
| `src/arbora/providers/__init__.py` | Provider package exports |
| `src/arbora/providers/base.py` | Provider-agnostic model protocol |
| `src/arbora/providers/echo.py` | Local stub provider (no network) |
| `src/arbora/providers/ollama.py` | Local Ollama HTTP provider (`gpt-oss:20b` default) |
| `src/arbora/cli/__init__.py` | CLI package marker |
| `src/arbora/cli/session.py` | Runtime wiring and plan formatting helpers |
| `src/arbora/cli/main.py` | Interactive and one-shot CLI chat shell |
| `tests/test_broker_and_planner.py` | Broker, planner, trust, and memory regression tests |
| `tests/test_memory_crypto.py` | Encrypted memory roundtrip, migration, and wipe tests |
| `tests/test_adapters_hardening.py` | Desktop/files/terminal hardening regression tests |
| `tests/test_browser_adapter.py` | Browser adapter and research journey tests |
| `tests/test_desktop_chat.py` | Tkinter desktop chat smoke tests |

---

## 007 — Tkinter desktop chat (2026-08-07)

| File | Change |
| --- | --- |
| `apps/desktop_chat/app.py` | Added Tkinter chat UI for plan→approve→execute |
| `apps/desktop_chat/__main__.py` | Added module entrypoint |
| `apps/desktop_chat/__init__.py` | Added package marker |
| `apps/__init__.py` | Added apps package marker |
| `apps/README.md` | Documented `arbora-ui` usage |
| `pyproject.toml` | Added `arbora-ui` script and apps package discovery |
| `tests/test_desktop_chat.py` | Added construction smoke tests |
| `docs/prototype.md` | Documented desktop UI; updated next spikes |
| `documentation/007-tkinter-desktop-chat.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 007 |
| `CHANGELOG.md` | Added file roles and section 007 |
| `README.md` | Pointed Documentation section at 007 |

---

## 006 — Browser adapter Playwright (2026-08-07)

| File | Change |
| --- | --- |
| `src/arbora/adapters/browser.py` | Added Playwright open/extract/save-brief/close actions |
| `src/arbora/adapters/__init__.py` | Exported `BrowserAdapter` |
| `src/arbora/cli/session.py` | Registered browser adapter in runtime |
| `src/arbora/core/planner.py` | Added research journey and browser allow-list |
| `pyproject.toml` | Added `playwright` dependency |
| `tests/test_browser_adapter.py` | Added URL validation, dry-run, and mocked browser tests |
| `docs/prototype.md` | Documented Chromium install and research demo |
| `documentation/006-browser-adapter-playwright.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 006 |
| `CHANGELOG.md` | Added file roles and section 006 |
| `README.md` | Pointed Documentation section at 006 |

---

## 005 — Harden Windows adapters (2026-08-05)

| File | Change |
| --- | --- |
| `src/arbora/adapters/powershell.py` | Added shared PowerShell runner with timeout and truncation |
| `src/arbora/adapters/desktop.py` | Added aliases, clearer launch errors, and `focus_window` |
| `src/arbora/adapters/files.py` | Expanded paths; clearer permission/OS errors |
| `src/arbora/adapters/terminal.py` | Switched to shared runner; surface timeouts |
| `src/arbora/adapters/__init__.py` | Exported shared runner helper |
| `src/arbora/core/planner.py` | Allowed `focus_window`; workday focuses Notepad |
| `tests/test_adapters_hardening.py` | Added adapter hardening tests |
| `docs/prototype.md` | Marked adapter hardening done; next spikes updated |
| `documentation/005-harden-windows-adapters.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 005 |
| `CHANGELOG.md` | Added file roles and section 005 |
| `README.md` | Pointed Documentation section at 005 |

---

## 004 — Encrypted local memory (2026-08-05)

| File | Change |
| --- | --- |
| `src/arbora/memory/crypto.py` | Added Fernet + Windows DPAPI / file-key crypto helpers |
| `src/arbora/memory/store.py` | Store preferences as `preferences.enc`; migrate plaintext JSON |
| `src/arbora/memory/__init__.py` | Exported crypto symbols |
| `src/arbora/cli/main.py` | Added `/memory` and `/wipe`; show encryption status at startup |
| `pyproject.toml` | Added `cryptography` dependency |
| `tests/test_memory_crypto.py` | Added encryption roundtrip, migration, and wipe tests |
| `docs/prototype.md` | Documented encrypted memory and wipe |
| `documentation/004-encrypted-local-memory.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 004 |
| `CHANGELOG.md` | Added file roles and section 004 |
| `README.md` | Pointed Documentation section at 004 |

---

## 003 — Trusted routines and local Ollama provider (2026-08-02)

| File | Change |
| --- | --- |
| `src/arbora/core/broker.py` | Auto-run matching trusted routines; hard confirms still enforced |
| `src/arbora/core/types.py` | Added `goal_norm` on trusted routines |
| `src/arbora/core/routines_store.py` | Added persistence helpers for trusted routines |
| `src/arbora/core/planner.py` | Added validated Ollama/JSON planning for unmatched goals |
| `src/arbora/providers/ollama.py` | Added local Ollama provider defaulting to `gpt-oss:20b` |
| `src/arbora/providers/__init__.py` | Exported `OllamaProvider` |
| `src/arbora/cli/session.py` | Wired provider selection and routine persistence |
| `src/arbora/cli/main.py` | Trusted-match UX, `--provider`, `/provider` |
| `tests/test_broker_and_planner.py` | Added trusted-reuse and provider-plan tests |
| `scripts/demo_journeys.py` | Forced echo provider for offline demo |
| `docs/prototype.md` | Documented Ollama + trusted-routine usage |
| `documentation/003-trusted-routines-and-ollama.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 003 |
| `CHANGELOG.md` | Added file roles and section 003 |
| `README.md` | Pointed Documentation section at 003 |

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
