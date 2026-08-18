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
| `documentation/008-setup-and-status-lights.md` | Change doc for Setup button and status lights |
| `documentation/009-packaging-and-first-run.md` | Change doc for packaging and first-run |
| `documentation/010-arbora-doctor.md` | Change doc for arbora doctor CLI |
| `documentation/011-trust-ux-routines-audit.md` | Change doc for Trust UX routines/audit dialogs |
| `documentation/012-emergency-stop.md` | Change doc for emergency stop |
| `documentation/013-journey-hardening.md` | Change doc for priority journey hardening |
| `documentation/014-richer-browser-actions.md` | Change doc for richer browser actions |
| `docs/prototype.md` | How to run and extend the Stage 1 prototype |
| `docs/NEXT.md` | Source of truth for near-term MVP build order |
| `docs/install.md` | Private-tester Windows install guide |
| `scripts/first_run.ps1` | One-shot venv + editable install for Windows testers |
| `apps/README.md` | Desktop chat run instructions |
| `apps/__init__.py` | Apps package marker |
| `apps/desktop_chat/__init__.py` | Desktop chat package marker |
| `apps/desktop_chat/__main__.py` | `python -m apps.desktop_chat` entry |
| `apps/desktop_chat/app.py` | Tkinter plan→approve→execute chat window |
| `scripts/demo_journeys.py` | Dry-run smoke demo of priority journeys |
| `src/arbora/__init__.py` | Package version and top-level identity |
| `src/arbora/setup_status.py` | Probe Memory/Ollama/Playwright and install Chromium |
| `src/arbora/core/__init__.py` | Core exports (broker, planner, audit, types) |
| `src/arbora/core/types.py` | Shared plan, step, scope, trust, and audit types |
| `src/arbora/core/audit.py` | Append-only in-memory audit log |
| `src/arbora/core/broker.py` | Permission broker — sole gate to tool side effects |
| `src/arbora/core/planner.py` | Goal → plan via templates and optional local model |
| `src/arbora/core/tool_catalog.py` | Shared allowed adapter/action catalog |
| `src/arbora/core/routines_store.py` | Serialize/load trusted routines for local memory |
| `src/arbora/adapters/__init__.py` | Adapter package exports |
| `src/arbora/adapters/powershell.py` | Shared PowerShell runner with timeout/truncation |
| `src/arbora/adapters/desktop.py` | Windows app list/launch/focus adapter |
| `src/arbora/adapters/file_undo.py` | Undo journal types for organise move batches |
| `src/arbora/adapters/files.py` | Files listing, organise apply/undo, write helpers |
| `src/arbora/adapters/terminal.py` | PowerShell execution adapter |
| `src/arbora/adapters/browser.py` | Playwright browser navigate/extract/brief adapter |
| `src/arbora/memory/__init__.py` | Memory package exports |
| `src/arbora/memory/crypto.py` | Fernet encryption and DPAPI/file key wrapping |
| `src/arbora/memory/store.py` | Encrypted on-device preferences key/value store |
| `src/arbora/providers/__init__.py` | Provider package exports |
| `src/arbora/providers/base.py` | Provider-agnostic model protocol |
| `src/arbora/providers/echo.py` | Local stub provider (no network) |
| `src/arbora/providers/ollama.py` | Local Ollama HTTP provider (`gpt-oss:20b` default) |
| `src/arbora/providers/openai_compatible.py` | Opt-in OpenAI-compatible cloud provider |
| `src/arbora/cli/__init__.py` | CLI package marker |
| `src/arbora/cli/session.py` | Runtime wiring and plan formatting helpers |
| `src/arbora/cli/main.py` | Interactive and one-shot CLI chat shell (+ doctor dispatch) |
| `src/arbora/cli/doctor.py` | `arbora doctor` health probes and fix hints |
| `tests/test_broker_and_planner.py` | Broker, planner, trust, and memory regression tests |
| `tests/test_memory_crypto.py` | Encrypted memory roundtrip, migration, and wipe tests |
| `tests/test_adapters_hardening.py` | Desktop/files/terminal hardening regression tests |
| `tests/test_browser_adapter.py` | Browser adapter and research journey tests |
| `tests/test_setup_status.py` | Status probe and first-run checklist regression tests |
| `tests/test_doctor.py` | arbora doctor CLI regression tests |
| `tests/test_desktop_chat.py` | Tkinter desktop chat and Trust UX dialog smoke tests |
| `tests/test_emergency_stop.py` | Broker emergency-stop skip and no-promote tests |
| `tests/test_file_undo.py` | Organise apply/undo roundtrip regression tests |
| `tests/test_openai_provider.py` | Opt-in cloud provider regression tests |
| `tests/test_workflow_packs.py` | Workflow pack load/match/plan tests |
| `src/arbora/schedules/store.py` | Serialize routine schedules in encrypted memory |
| `src/arbora/schedules/runner.py` | Due-time checks and trusted-only schedule execution |
| `src/arbora/schedules/__init__.py` | Schedules package exports |
| `src/arbora/cli/schedule.py` | `arbora schedule` CLI for trusted-routine triggers |
| `tests/test_schedules.py` | Schedule store/run/CLI regression tests |
| `src/arbora/core/audit_store.py` | Serialize and cap persisted audit events in memory |
| `tests/test_audit_persistence.py` | Audit persistence across sessions regression tests |
| `src/arbora/cli/validate.py` | `arbora validate` MVP exit-criteria dry-run checks |
| `tests/test_validate.py` | MVP validate CLI regression tests |
| `src/arbora/preferences/store.py` | Opt-in user preference serialization |
| `src/arbora/cli/prefs.py` | `arbora prefs` CLI |
| `tests/test_preferences.py` | User preference regression tests |
| `workflows/dev-project-setup.json` | Bundled developer project scaffold workflow pack |
| `src/arbora/cli/audit_cmd.py` | `arbora audit export` JSON export command |
| `tests/test_audit_export.py` | Audit export regression tests |
| `workflows/organise-downloads.json` | Bundled organise Downloads preview→apply workflow pack |
| `src/arbora/voice/windows.py` | Windows System.Speech voice-to-text helper |
| `tests/test_voice_windows.py` | Voice input helper regression tests |
| `workflows/git-status.json` | Read-only git status/diff workflow pack |
| `src/arbora/memory/goal_history.py` | Recent goal history in encrypted memory |
| `tests/test_goal_history.py` | Goal history regression tests |
| `documentation/033-downloads-folder-preference.md` | Change doc for downloads folder preference |
| `documentation/034-save-note-journey.md` | Change doc for save-note journey |
| `documentation/035-local-memory-export.md` | Change doc for local memory export |
| `src/arbora/cli/memory_cmd.py` | `arbora memory status|export` command |
| `tests/test_memory_export.py` | Memory export regression tests |

---

## 035 — Local memory export (2026-08-18)

| File | Change |
| --- | --- |
| `src/arbora/memory/store.py` | Added JSON export payload and status rows (no key material) |
| `src/arbora/memory/__init__.py` | Exported memory export helpers |
| `src/arbora/cli/memory_cmd.py` | Added `arbora memory status` and `export` |
| `src/arbora/cli/main.py` | Dispatch + `/memory export` |
| `apps/desktop_chat/app.py` | Memory dialog with Export JSON |
| `tests/test_memory_export.py` | Added memory export tests |
| `tests/test_desktop_chat.py` | Added memory status formatter test |
| `docs/NEXT.md` | Marked P8#27 done |
| `documentation/035-local-memory-export.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 035 |
| `README.md` | Linked document 035 |
| `CHANGELOG.md` | Added file roles and 035 section |

---

## 034 — Save-note journey (2026-08-18)

| File | Change |
| --- | --- |
| `src/arbora/preferences/store.py` | Added `notes_folder` preference |
| `src/arbora/core/planner.py` | Added save-note journey and timestamped write plan |
| `src/arbora/cli/session.py` | Pass `notes_root` into planner |
| `src/arbora/cli/main.py` | Documented notes preference and example goal |
| `src/arbora/cli/prefs.py` | Listed `notes_folder` in set-key help |
| `tests/test_preferences.py` | Added notes folder + live write tests |
| `tests/test_broker_and_planner.py` | Added save-note phrasing test |
| `docs/NEXT.md` | Marked P8#26 done |
| `documentation/034-save-note-journey.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 034 |
| `README.md` | Linked document 034 |
| `CHANGELOG.md` | Added file roles and 034 section |

---

## 033 — Downloads folder preference (2026-08-18)

| File | Change |
| --- | --- |
| `src/arbora/preferences/store.py` | Added `downloads_folder` preference |
| `src/arbora/core/planner.py` | Organise, list, and fallback plans use configured downloads root |
| `src/arbora/cli/session.py` | Pass `downloads_root` into planner |
| `src/arbora/cli/main.py` | Documented `downloads_folder` in banner |
| `src/arbora/cli/prefs.py` | Listed `downloads_folder` in set-key help |
| `tests/test_preferences.py` | Added downloads folder preference tests |
| `tests/test_file_undo.py` | Organise runtime test uses downloads preference |
| `docs/NEXT.md` | Added P8 plates; marked #25 done |
| `documentation/033-downloads-folder-preference.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 033 |
| `README.md` | Linked document 033 |
| `CHANGELOG.md` | Added file roles and 033 section |

---

## 032 — Recent goal history (2026-08-18)

| File | Change |
| --- | --- |
| `src/arbora/memory/goal_history.py` | Added record/list recent goals helpers |
| `src/arbora/cli/main.py` | `/history` command + record on plan |
| `apps/desktop_chat/app.py` | History picker + record on plan |
| `tests/test_goal_history.py` | Added goal history tests |
| `docs/NEXT.md` | Marked P7#24 done |
| `documentation/032-recent-goal-history.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 032 |
| `README.md` | Linked document 032 |
| `CHANGELOG.md` | Added file roles and 032 section |

---

## 031 — Projects folder preference (2026-08-18)

| File | Change |
| --- | --- |
| `src/arbora/preferences/store.py` | Added `projects_folder` preference |
| `src/arbora/core/planner.py` | Dev setup and workday shutdown use configured roots |
| `src/arbora/cli/session.py` | Pass `projects_root` into planner |
| `src/arbora/cli/main.py` | Documented `projects_folder` in banner |
| `tests/test_preferences.py` | Added projects folder preference tests |
| `docs/NEXT.md` | Marked P7#23 done |
| `documentation/031-projects-folder-preference.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 031 |
| `README.md` | Linked document 031 |
| `CHANGELOG.md` | Added file roles and 031 section |

---

## 030 — Git status workflow pack (2026-08-18)

| File | Change |
| --- | --- |
| `workflows/git-status.json` | Added read-only git status workflow pack |
| `tests/test_workflow_packs.py` | Added git status pack tests |
| `docs/NEXT.md` | Added P7 plates; marked #22 done |
| `documentation/030-git-status-workflow-pack.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 030 |
| `README.md` | Linked document 030 |
| `CHANGELOG.md` | Added file roles and 030 section |

---

## 029 — Windows voice input (2026-08-17)

| File | Change |
| --- | --- |
| `src/arbora/voice/windows.py` | Added System.Speech listen helper |
| `src/arbora/voice/__init__.py` | Voice package exports |
| `apps/desktop_chat/app.py` | Added Voice button and background listener |
| `tests/test_voice_windows.py` | Added voice helper tests |
| `docs/NEXT.md` | Marked P6#21 done |
| `documentation/029-windows-voice-input.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 029 |
| `README.md` | Linked document 029 |
| `CHANGELOG.md` | Added file roles and 029 section |

---

## 028 — Briefs folder preference (2026-08-17)

| File | Change |
| --- | --- |
| `src/arbora/preferences/store.py` | Added `briefs_folder` preference |
| `src/arbora/core/planner.py` | Research journey uses configured briefs root |
| `src/arbora/cli/session.py` | Pass `briefs_root` into planner |
| `src/arbora/cli/main.py` | Documented `briefs_folder` in banner |
| `tests/test_preferences.py` | Added briefs folder preference tests |
| `docs/NEXT.md` | Marked P6#20 done |
| `documentation/028-briefs-folder-preference.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 028 |
| `README.md` | Linked document 028 |
| `CHANGELOG.md` | Added file roles and 028 section |

---

## 027 — Research journey snapshot (2026-08-17)

| File | Change |
| --- | --- |
| `src/arbora/core/planner.py` | Added snapshot step to research journey |
| `workflows/research-example.json` | Added snapshot step to example pack |
| `tests/test_browser_adapter.py` | Assert research plan includes snapshot |
| `docs/NEXT.md` | Added P6 plates; marked #19 done |
| `documentation/027-research-journey-snapshot.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 027 |
| `README.md` | Linked document 027 |
| `CHANGELOG.md` | Added file roles and 027 section |

---

## 026 — Startup schedule runner (2026-08-16)

| File | Change |
| --- | --- |
| `src/arbora/preferences/store.py` | Added `run_due_schedules_on_start` preference |
| `apps/desktop_chat/app.py` | Run due schedules on startup when opted in |
| `src/arbora/cli/main.py` | Documented preference in banner |
| `tests/test_preferences.py` | Added startup schedule preference tests |
| `docs/NEXT.md` | Marked P5#18 done |
| `documentation/026-startup-schedule-runner.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 026 |
| `README.md` | Linked document 026 |
| `CHANGELOG.md` | Added file roles and 026 section |

---

## 025 — Organise downloads workflow pack (2026-08-16)

| File | Change |
| --- | --- |
| `workflows/organise-downloads.json` | Added organise Downloads workflow pack |
| `tests/test_workflow_packs.py` | Added organise pack match tests |
| `docs/NEXT.md` | Marked P5#17 done |
| `documentation/025-organise-downloads-workflow-pack.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 025 |
| `README.md` | Linked document 025 |
| `CHANGELOG.md` | Added file roles and 025 section |

---

## 024 — Audit export (2026-08-16)

| File | Change |
| --- | --- |
| `src/arbora/core/audit_store.py` | Added `export_audit_payload` helper |
| `src/arbora/cli/audit_cmd.py` | Added `arbora audit export` |
| `src/arbora/cli/main.py` | Dispatch audit CLI + `/audit export` |
| `apps/desktop_chat/app.py` | Added Export JSON button in Audit dialog |
| `tests/test_audit_export.py` | Added audit export tests |
| `docs/NEXT.md` | Added P5 plates; marked #16 done |
| `documentation/024-audit-export.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 024 |
| `README.md` | Linked document 024 |
| `CHANGELOG.md` | Added file roles and 024 section |

---

## 023 — Developer project workflow pack (2026-08-15)

| File | Change |
| --- | --- |
| `workflows/dev-project-setup.json` | Added developer scaffold workflow pack |
| `src/arbora/core/planner.py` | Hardened dev setup journey with README/.gitignore writes |
| `tests/test_workflow_packs.py` | Added dev pack and scaffold journey tests |
| `docs/NEXT.md` | Marked P4#15 done |
| `documentation/023-dev-project-workflow-pack.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 023 |
| `README.md` | Linked document 023 |
| `CHANGELOG.md` | Added file roles and 023 section |

---

## 022 — Opt-in user preferences (2026-08-15)

| File | Change |
| --- | --- |
| `src/arbora/preferences/store.py` | Added preference load/save/set helpers |
| `src/arbora/preferences/__init__.py` | Preferences package exports |
| `src/arbora/cli/prefs.py` | Added `arbora prefs list|set` |
| `src/arbora/cli/session.py` | Apply preferences in `build_runtime` |
| `src/arbora/cli/main.py` | `/prefs` command + dry-run default from prefs |
| `src/arbora/core/planner.py` | Workday journey uses configured folder |
| `apps/desktop_chat/app.py` | Load dry-run/provider defaults from prefs |
| `tests/test_preferences.py` | Added preference regression tests |
| `docs/NEXT.md` | Marked P4#14 done |
| `documentation/022-opt-in-user-preferences.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 022 |
| `README.md` | Linked document 022 |
| `CHANGELOG.md` | Added file roles and 022 section |

---

## 021 — MVP validate CLI (2026-08-15)

| File | Change |
| --- | --- |
| `src/arbora/cli/validate.py` | Added five MVP exit-criteria checks |
| `src/arbora/cli/main.py` | Dispatch `arbora validate` + banner line |
| `tests/test_validate.py` | Added validate regression tests |
| `docs/NEXT.md` | Added P4 plates; marked #13 done |
| `documentation/021-mvp-validate-cli.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 021 |
| `README.md` | Linked document 021 |
| `CHANGELOG.md` | Added file roles and 021 section |

---

## 020 — Persistent audit log (2026-08-13)

| File | Change |
| --- | --- |
| `src/arbora/core/audit_store.py` | Added audit event load/persist helpers |
| `src/arbora/core/audit.py` | Added preload + on_record persistence hook |
| `src/arbora/cli/session.py` | Wire audit persistence in `build_runtime` |
| `apps/desktop_chat/app.py` | Updated audit dialog copy for persisted log |
| `tests/test_audit_persistence.py` | Added persistence/trim/wipe tests |
| `tests/test_desktop_chat.py` | Updated empty audit message |
| `docs/NEXT.md` | Marked P3#11 done; MVP plates complete |
| `documentation/020-persistent-audit-log.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 020 |
| `README.md` | Linked document 020 |
| `CHANGELOG.md` | Added file roles and 020 section |

---

## 019 — Desktop schedule UX (2026-08-13)

| File | Change |
| --- | --- |
| `apps/desktop_chat/app.py` | Added Schedules dialog (add/remove/toggle) |
| `tests/test_desktop_chat.py` | Added schedule list helper and dialog smoke tests |
| `docs/NEXT.md` | Marked P3#12 done |
| `documentation/019-desktop-schedule-ux.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 019 |
| `README.md` | Linked document 019 |
| `CHANGELOG.md` | Added file roles and 019 section |

---

## 018 — Scheduled trusted routines (2026-08-13)

| File | Change |
| --- | --- |
| `src/arbora/core/types.py` | Added `goal_text` on trusted routines for stable replans |
| `src/arbora/core/broker.py` | Store original goal text when promoting routines |
| `src/arbora/core/routines_store.py` | Serialize `goal_text` for trusted routines |
| `src/arbora/schedules/runner.py` | Added due checks and trusted-only runner |
| `src/arbora/schedules/__init__.py` | Schedules package marker |
| `src/arbora/cli/schedule.py` | Added `arbora schedule` subcommands |
| `src/arbora/cli/main.py` | Dispatch schedule CLI + `/schedules` command |
| `tests/test_schedules.py` | Added schedule regression tests |
| `docs/NEXT.md` | Marked P2#10 done; added P3 plates |
| `documentation/018-scheduled-trusted-routines.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 018 |
| `README.md` | Linked document 018 |
| `CHANGELOG.md` | Added file roles and 018 section |

---

## 017 — Reusable workflow packs (2026-08-12)

| File | Change |
| --- | --- |
| `src/arbora/workflows/packs.py` | Added workflow pack loader and matcher |
| `src/arbora/workflows/__init__.py` | Workflows package marker |
| `src/arbora/core/tool_catalog.py` | Shared allowed adapter/action catalog |
| `workflows/*.json` | Bundled example workflow packs |
| `workflows/README.md` | Documented pack format |
| `src/arbora/core/planner.py` | Match workflow packs before provider fallback |
| `src/arbora/cli/main.py` | Added `/workflows` command |
| `tests/test_workflow_packs.py` | Added workflow pack tests |
| `docs/NEXT.md` | Marked P2#9 done |
| `docs/prototype.md` | Linked workflow packs |
| `documentation/017-workflow-packs.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 017 |
| `CHANGELOG.md` | Added file roles and section 017 |
| `README.md` | Pointed Documentation section at 017 |

---

## 016 — Opt-in OpenAI-compatible cloud provider (2026-08-12)

| File | Change |
| --- | --- |
| `src/arbora/providers/openai_compatible.py` | Added OpenAI-compatible cloud provider |
| `src/arbora/providers/__init__.py` | Exported cloud provider helpers |
| `src/arbora/cli/session.py` | Provider selection, privacy notice, choice list |
| `src/arbora/cli/main.py` | Cloud privacy notice in banner and `/provider` |
| `apps/desktop_chat/app.py` | Cloud provider option + privacy banner |
| `tests/test_openai_provider.py` | Added mocked cloud provider tests |
| `docs/NEXT.md` | Marked P2#8 done |
| `documentation/016-opt-in-cloud-provider.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 016 |
| `CHANGELOG.md` | Added file roles and section 016 |
| `README.md` | Pointed Documentation section at 016 |

---

## 015 — File undo for organise moves (2026-08-12)

| File | Change |
| --- | --- |
| `src/arbora/adapters/file_undo.py` | Added undo batch journal helpers |
| `src/arbora/adapters/files.py` | Added apply_organise and undo_last_organise |
| `src/arbora/cli/session.py` | Wired undo journal to encrypted local memory |
| `src/arbora/cli/main.py` | Added `/undo` shortcut and banner help |
| `src/arbora/core/planner.py` | Organise apply step + undo journey matcher |
| `tests/test_file_undo.py` | Added apply/undo tests |
| `docs/NEXT.md` | Marked P1#7 done |
| `documentation/015-file-undo-organise.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 015 |
| `CHANGELOG.md` | Added file roles and section 015 |
| `README.md` | Pointed Documentation section at 015 |

---

## 014 — Richer broker-gated browser actions (2026-08-09)

| File | Change |
| --- | --- |
| `src/arbora/adapters/browser.py` | Added click, type_text, wait_for, snapshot |
| `src/arbora/core/planner.py` | Allowed new browser actions in provider plans |
| `tests/test_browser_adapter.py` | Added interaction/snapshot tests |
| `docs/NEXT.md` | Marked P1#6 done |
| `docs/prototype.md` | Noted richer browser done |
| `documentation/014-richer-browser-actions.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 014 |
| `CHANGELOG.md` | Added file roles and section 014 |
| `README.md` | Pointed Documentation section at 014 |

---

## 013 — Journey hardening for priority plans (2026-08-09)

| File | Change |
| --- | --- |
| `src/arbora/core/planner.py` | Hardened workday/diagnose/research/dev templates and matchers |
| `tests/test_broker_and_planner.py` | Added phrasing and network-step assertions |
| `tests/test_browser_adapter.py` | Assert research ensure_directory + look-up phrasing |
| `docs/NEXT.md` | Marked P1#5 done |
| `docs/prototype.md` | Noted journey hardening done |
| `documentation/013-journey-hardening.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 013 |
| `CHANGELOG.md` | Added file roles and section 013 |
| `README.md` | Pointed Documentation section at 013 |

---

## 012 — Emergency stop for in-flight plans (2026-08-09)

| File | Change |
| --- | --- |
| `src/arbora/core/broker.py` | Added stop flag; skip remaining steps and audit halt |
| `apps/desktop_chat/app.py` | Background Approve & run + Stop button |
| `apps/README.md` | Documented emergency Stop |
| `tests/test_emergency_stop.py` | Added stop regression tests |
| `docs/NEXT.md` | Marked P0#4 done |
| `docs/prototype.md` | Noted emergency stop done |
| `documentation/012-emergency-stop.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 012 |
| `CHANGELOG.md` | Added file roles and section 012 |
| `README.md` | Pointed Documentation section at 012 |

---

## 011 — Trust UX for routines and audit (2026-08-08)

| File | Change |
| --- | --- |
| `apps/desktop_chat/app.py` | Added Routines revoke dialog and Audit dialog |
| `apps/README.md` | Documented Trust UX dialogs |
| `tests/test_desktop_chat.py` | Added dialog smoke tests |
| `docs/NEXT.md` | Marked P0#3 done |
| `docs/prototype.md` | Noted Trust UX done |
| `documentation/011-trust-ux-routines-audit.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 011 |
| `CHANGELOG.md` | Added file roles and section 011 |
| `README.md` | Pointed Documentation section at 011 |

---

## 010 — arbora doctor health checks (2026-08-08)

| File | Change |
| --- | --- |
| `src/arbora/cli/doctor.py` | Added doctor probes with text/JSON output and exit codes |
| `src/arbora/cli/main.py` | Dispatch `arbora doctor`; mention in banner |
| `tests/test_doctor.py` | Added doctor tests |
| `docs/install.md` | Documented doctor verify step |
| `docs/prototype.md` | Noted doctor plate done |
| `docs/NEXT.md` | Marked P0#2 done |
| `documentation/010-arbora-doctor.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 010 |
| `CHANGELOG.md` | Added file roles and section 010 |
| `README.md` | Pointed Documentation section at 010 |

---

## 009 — Packaging and first-run for private testers (2026-08-08)

| File | Change |
| --- | --- |
| `scripts/first_run.ps1` | Added Windows one-shot venv + install script |
| `docs/install.md` | Added private-tester install guide |
| `src/arbora/setup_status.py` | Added fix hints and first-run checklist helpers |
| `apps/desktop_chat/app.py` | Setup dialog shows first-run checklist |
| `apps/README.md` | Pointed testers at first_run.ps1 |
| `CONTRIBUTING.md` | Documented preferred first-run setup |
| `docs/prototype.md` | Linked install path; noted P0#1 done |
| `docs/NEXT.md` | Marked packaging plate done |
| `tests/test_setup_status.py` | Added checklist / fix-hint tests |
| `documentation/009-packaging-and-first-run.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 009 |
| `CHANGELOG.md` | Added file roles and section 009 |
| `README.md` | Linked install docs and Documentation 009 |

---

## 008 — Setup button and connection status lights (2026-08-07)

| File | Change |
| --- | --- |
| `src/arbora/setup_status.py` | Added service probes and Chromium install helper |
| `apps/desktop_chat/app.py` | Added Connections lights, Setup dialog, Refresh status |
| `apps/README.md` | Documented Setup and status lights |
| `tests/test_setup_status.py` | Added probe tests |
| `documentation/008-setup-and-status-lights.md` | Recorded this change set |
| `documentation/README.md` | Indexed document 008 |
| `CHANGELOG.md` | Added file roles and section 008 |
| `README.md` | Pointed Documentation section at 008 |

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
