# Documentation index

Numbered change documents for Arbora. Each git commit that lands meaningful work should add the next `NNN-*.md` file here (see [CONTRIBUTING.md](../CONTRIBUTING.md)).

| No. | Document | Date | Summary |
| --- | --- | --- | --- |
| 001 | [Stage 1 prototype bootstrap](001-stage1-prototype-bootstrap.md) | 2026-08-02 | GPL license, permission broker, Windows adapters, CLI plan→approve→execute loop |
| 002 | [Commit documentation process](002-commit-documentation-process.md) | 2026-08-02 | Numbered docs process and per-file CHANGELOG |
| 003 | [Trusted routines and local Ollama](003-trusted-routines-and-ollama.md) | 2026-08-02 | Trusted-routine reuse + Ollama `gpt-oss:20b` planning |
| 004 | [Encrypted local memory](004-encrypted-local-memory.md) | 2026-08-05 | Fernet at-rest encryption + Windows DPAPI key wrap |
| 005 | [Harden Windows adapters](005-harden-windows-adapters.md) | 2026-08-05 | Shared PowerShell runner, aliases, focus, clearer errors |
| 006 | [Browser adapter (Playwright)](006-browser-adapter-playwright.md) | 2026-08-07 | Navigate/extract/save brief via Chromium behind the broker |
| 007 | [Tkinter desktop chat](007-tkinter-desktop-chat.md) | 2026-08-07 | Native plan→approve→execute chat window |
| 012 | [Emergency stop](012-emergency-stop.md) | 2026-08-09 | Halt in-flight plans between steps from the desktop UI |
| 011 | [Trust UX routines/audit](011-trust-ux-routines-audit.md) | 2026-08-08 | Desktop dialogs to inspect/revoke routines and read audit |
| 010 | [arbora doctor](010-arbora-doctor.md) | 2026-08-08 | CLI health probes with fix hints |
| 009 | [Packaging and first-run](009-packaging-and-first-run.md) | 2026-08-08 | Windows first-run script + Setup checklist for private testers |
| 008 | [Setup and status lights](008-setup-and-status-lights.md) | 2026-08-07 | Setup dialog + red/yellow/green connection lights |

Design notes and ADRs that are not commit-tied live under [`docs/`](../docs/). Near-term build order: [`docs/NEXT.md`](../docs/NEXT.md).

Per-file roles and one-line change summaries: [`CHANGELOG.md`](../CHANGELOG.md).
