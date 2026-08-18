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
| 031 | [Projects folder preference](031-projects-folder-preference.md) | 2026-08-18 | User-configurable dev projects directory |
| 030 | [Git status workflow pack](030-git-status-workflow-pack.md) | 2026-08-18 | Read-only git status/diff workflow pack |
| 029 | [Windows voice input](029-windows-voice-input.md) | 2026-08-17 | Push-to-talk goal entry in arbora-ui via System.Speech |
| 028 | [Briefs folder preference](028-briefs-folder-preference.md) | 2026-08-17 | User-configurable research output directory |
| 027 | [Research journey snapshot](027-research-journey-snapshot.md) | 2026-08-17 | Research plans save a page snapshot before the brief |
| 026 | [Startup schedule runner](026-startup-schedule-runner.md) | 2026-08-16 | Opt-in run-due-schedules when arbora-ui starts |
| 025 | [Organise downloads workflow pack](025-organise-downloads-workflow-pack.md) | 2026-08-16 | Preview→apply Downloads filing workflow pack |
| 024 | [Audit export](024-audit-export.md) | 2026-08-16 | Export persisted audit log as JSON |
| 023 | [Developer project workflow pack](023-dev-project-workflow-pack.md) | 2026-08-15 | Dev scaffold pack + hardened set-up-a-project journey |
| 022 | [Opt-in user preferences](022-opt-in-user-preferences.md) | 2026-08-15 | Encrypted defaults for dry-run, provider, workday folder |
| 021 | [MVP validate CLI](021-mvp-validate-cli.md) | 2026-08-15 | `arbora validate` dry-runs MVP exit criteria |
| 020 | [Persistent audit log](020-persistent-audit-log.md) | 2026-08-13 | Audit events survive restarts in encrypted local memory |
| 019 | [Desktop schedule UX](019-desktop-schedule-ux.md) | 2026-08-13 | Schedules dialog in arbora-ui for trusted-routine triggers |
| 018 | [Scheduled trusted routines](018-scheduled-trusted-routines.md) | 2026-08-13 | Time triggers for trusted routines via `arbora schedule` |
| 017 | [Workflow packs](017-workflow-packs.md) | 2026-08-12 | JSON workflow packs loadable into promotable plans |
| 016 | [Opt-in cloud provider](016-opt-in-cloud-provider.md) | 2026-08-12 | OpenAI-compatible provider + privacy banner |
| 015 | [File undo for organise moves](015-file-undo-organise.md) | 2026-08-12 | apply_organise + undo_last_organise with local journal |
| 014 | [Richer browser actions](014-richer-browser-actions.md) | 2026-08-09 | Click/type/wait/snapshot behind the browser broker gate |
| 013 | [Journey hardening](013-journey-hardening.md) | 2026-08-09 | Stronger workday/diagnose/research plans and matchers |
| 012 | [Emergency stop](012-emergency-stop.md) | 2026-08-09 | Halt in-flight plans between steps from the desktop UI |
| 011 | [Trust UX routines/audit](011-trust-ux-routines-audit.md) | 2026-08-08 | Desktop dialogs to inspect/revoke routines and read audit |
| 010 | [arbora doctor](010-arbora-doctor.md) | 2026-08-08 | CLI health probes with fix hints |
| 009 | [Packaging and first-run](009-packaging-and-first-run.md) | 2026-08-08 | Windows first-run script + Setup checklist for private testers |
| 008 | [Setup and status lights](008-setup-and-status-lights.md) | 2026-08-07 | Setup dialog + red/yellow/green connection lights |

Design notes and ADRs that are not commit-tied live under [`docs/`](../docs/). Near-term build order: [`docs/NEXT.md`](../docs/NEXT.md).

Per-file roles and one-line change summaries: [`CHANGELOG.md`](../CHANGELOG.md).
