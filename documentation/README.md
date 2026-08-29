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
| 058 | [Close window by title](058-close-window-by-title.md) | 2026-08-28 | WM_CLOSE to a titled window; not taskkill |
| 059 | [Open URL in installed Chrome/Edge](059-open-url-installed-browser.md) | 2026-08-28 | Start-Process http(s) URL in Chrome/Edge; not Playwright |
| 060 | [Printer inspect](060-inspect-printers.md) | 2026-08-28 | Read-only default/list printers; no jobs or secrets |
| 061 | [Recent files in Documents](061-recent-files-documents.md) | 2026-08-29 | Newest-first listing of Documents behind the broker |
| 062 | [Startup apps inspect](062-inspect-startup.md) | 2026-08-29 | Read-only HKCU/HKLM Run + Startup folder; no enable/disable |
| 063 | [Default browser inspect](063-inspect-default-browser.md) | 2026-08-29 | Read-only http(s) UserChoice ProgId; no association changes |
| 055 | [Save clipboard to notes](055-save-clipboard-to-notes.md) | 2026-08-27 | Clipboard text to notes_folder; secrets/non-text refused |
| 056 | [Empty old Downloads](056-empty-old-downloads.md) | 2026-08-27 | Preview then hard-confirm delete of old top-level Downloads files |
| 057 | [Battery / power inspect](057-inspect-battery.md) | 2026-08-27 | Read-only battery charge and chassis status; no secrets |
| 052 | [Copy or move a file with preview](052-copy-move-file.md) | 2026-08-24 | Preview then copy/move one file; move can undo |
| 053 | [Screenshot / window snapshot](053-capture-screenshot.md) | 2026-08-24 | Broker-gated PNG capture of screen or titled window |
| 054 | [Network / wifi inspect](054-inspect-network.md) | 2026-08-24 | Read-only adapters and IPv4; no Wi-Fi keys |
| 051 | [Opt-in spoken confirmations](051-spoken-confirmations.md) | 2026-08-22 | TTS plan read-back; broker-gated; no always-on mic |
| 050 | [Clipboard inspect](050-clipboard-inspect.md) | 2026-08-22 | Type/length inspect; secrets withheld |
| 049 | [Recent files in Downloads](049-recent-files-downloads.md) | 2026-08-22 | Newest-first listing behind the broker |
| 048 | [Everyday app launch aliases](048-app-launch-aliases.md) | 2026-08-21 | Chrome / Edge / VS Code resolve on launch_app |
| 047 | [Temp inspect and clean](047-temp-inspect-clean.md) | 2026-08-21 | Preview user TEMP; clean needs hard confirmation |
| 046 | [Find files by name](046-find-files-by-name.md) | 2026-08-21 | Depth-capped filename search behind the broker |
| 045 | [Recycle Bin inspect and empty](045-recycle-bin-inspect-empty.md) | 2026-08-20 | Preview Recycle Bin; empty needs hard confirmation |
| 044 | [Open folder in Explorer](044-open-folder-explorer.md) | 2026-08-20 | List then open a folder in File Explorer |
| 043 | [Voice listen UX polish](043-voice-listen-ux.md) | 2026-08-20 | Disable Voice while listening; culture + confidence |
| 042 | [GitHub Actions PR gates](042-github-actions-pr-gates.md) | 2026-08-19 | pytest + arbora validate on PRs to main; branch-protection how-to |
| 041 | [Pytest workflow pack](041-pytest-workflow-pack.md) | 2026-08-19 | Broker-gated python -m pytest for the current directory |
| 040 | [Largest-folder disk journey](040-largest-folder-disk-journey.md) | 2026-08-19 | Read-only C:\\ folder ranking; Format-Table is not destructive |
| 039 | [GitHub Actions pytest CI](039-github-actions-pytest.md) | 2026-08-19 | Windows pytest on pushes and PRs to main and dev |
| 038 | [Larger desktop Trust dialogs](038-larger-desktop-dialogs.md) | 2026-08-19 | Enlarge Audit/Memory/Routines windows so buttons stay visible |
| 037 | [Sample read-only trusted routines](037-sample-read-only-routines.md) | 2026-08-19 | First-run list-downloads and disk-diagnose samples |
| 036 | [Fix desktop voice import](036-fix-desktop-voice-import.md) | 2026-08-18 | Import Voice button helpers in arbora-ui |
| 035 | [Local memory export](035-local-memory-export.md) | 2026-08-18 | Export encrypted-memory contents as JSON |
| 034 | [Save-note journey](034-save-note-journey.md) | 2026-08-18 | Notes folder preference + local save-note plan |
| 033 | [Downloads folder preference](033-downloads-folder-preference.md) | 2026-08-18 | User-configurable organise/list directory |
| 032 | [Recent goal history](032-recent-goal-history.md) | 2026-08-18 | Persist and recall recent goals locally |
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
