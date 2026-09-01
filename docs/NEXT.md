# Arbora — what we do next

**Status:** living source of truth for near-term product work  
**Audience:** anyone building or reviewing Arbora  
**Relationship to other docs:**

| Document | Job |
| --- | --- |
| [README.md](../README.md) | Product vision, safety contract, long-term roadmap stages |
| [docs/prototype.md](prototype.md) | How to run what exists today |
| [documentation/](../documentation/README.md) | What already shipped (commit-tied history) |
| **This file** | Ordered plates for the next stretch toward MVP |

When this file disagrees with casual chat notes, **this file wins**. Update it when priorities change.

---

## Current position

Arbora is past Stage 1 bootstrap and early into **Stage 2 (MVP)**.

Already in place:

- permission broker with plan → approve → execute;
- trusted routines + hard confirmations;
- Windows adapters: desktop, files, terminal, browser (research-thin);
- encrypted local memory;
- local Ollama provider + echo stub;
- CLI (`arbora`) and Tkinter UI (`arbora-ui`);
- Setup dialog + connection status lights;
- private-tester first-run path (`scripts/first_run.ps1` + Setup checklist);
- `arbora doctor` health checks;
- desktop Trust UX (routines revoke + audit dialogs);
- emergency stop for in-flight plans (broker + desktop Stop);
- hardened priority journey templates (workday / diagnose / research);
- richer browser actions (click / type / wait / snapshot);
- file undo for organise moves (apply + reverse last batch);
- opt-in OpenAI-compatible cloud provider with privacy banner;
- reusable workflow packs (bundled JSON + user overrides);
- scheduled trusted routines (`arbora schedule` + `/schedules`);
- desktop schedule management in `arbora-ui`;
- persistent audit log across sessions (encrypted local memory).
- largest-folder disk ranking for “what is using space on C”;
- pytest suite run behind the broker for the current directory;
- GitHub Actions pytest + `arbora validate` on pull requests to `main`;
- desktop Voice listen that cannot double-fire and reports confidence;
- open Downloads or Desktop in File Explorer behind the broker;
- Recycle Bin inspect / empty;
- depth-capped filename search (`find invoice.pdf in downloads`);
- user TEMP inspect, with clean only after hard confirmation;
- everyday app aliases so “open chrome” launches the installed browser.
- newest-first listing of recent files in Downloads.
- newest-first listing of recent files in Documents.
- clipboard inspect (type/length; secrets withheld).
- save clipboard text to the notes folder (secrets/non-text refused).
- preview then delete top-level Downloads files older than N days (hard confirm).
- read-only battery charge and AC/chassis status.
- close a titled window with WM_CLOSE (not taskkill / Stop-Process).
- open an http(s) URL in installed Chrome/Edge (Start-Process, not Playwright).
- read-only installed printers and the default printer (no jobs or secrets).
- read-only startup apps (HKCU/HKLM Run names + user Startup folder).
- read-only default http(s) browser (UserChoice ProgId; no association changes).
- read-only attached displays and resolutions (no mode changes).
- read-only last Windows Update install date (does not install updates).
- read-only time zone and locale (no tzutil / Set-Culture).
- opt-in spoken plan read-back (TTS, still broker-gated; no always-on mic).
- user-configurable `screenshots_folder` for capture (defaults under notes).
- preview then copy or move one file (overwrite refused; move can undo).
- broker-gated screenshot / window PNG under `screenshots_folder` (default notes/screenshots).
- read-only network adapter and IPv4 inspect (no Wi-Fi keys).

Stage 2 MVP capability plates in [docs/NEXT.md](docs/NEXT.md) are complete. Stage 3 work continues (see P4–P18).

---

### P4 — Stage 3 personal depth (in progress)

| # | Plate | Done when |
| --- | --- | --- |
| 13 | **MVP validate CLI** | ✅ `arbora validate` dry-runs the five MVP exit criteria |
| 14 | **Opt-in user preferences** | ✅ User-set defaults in encrypted memory (`/prefs`, planner hooks) |
| 15 | **Developer project workflow pack** | ✅ Bundled dev scaffold pack + hardened setup journey |

### P5 — Stage 3 depth (in progress)

| # | Plate | Done when |
| --- | --- | --- |
| 16 | **Audit export** | ✅ Export persisted audit log as JSON (CLI + desktop) |
| 17 | **Organise downloads workflow pack** | ✅ Bundled preview→apply organise pack with undo path |
| 18 | **Startup schedule runner** | ✅ Opt-in run-due-schedules when `arbora-ui` starts |

### P6 — Stage 3 research and voice (in progress)

| # | Plate | Done when |
| --- | --- | --- |
| 19 | **Research journey snapshot** | ✅ Research plans save a local page snapshot before the brief |
| 20 | **Briefs folder preference** | ✅ User-configurable `briefs_folder` for research output |
| 21 | **Windows voice input** | ✅ Opt-in push-to-talk goal entry in `arbora-ui` |

### P7 — Stage 3 developer and memory (in progress)

| # | Plate | Done when |
| --- | --- | --- |
| 22 | **Git status workflow pack** | ✅ Read-only git status/diff pack for the current directory |
| 23 | **Projects folder preference** | ✅ User-configurable `projects_folder` for dev setup |
| 24 | **Recent goal history** | ✅ Persist and recall recent goals (`/history`, desktop picker) |

### P8 — Stage 3 organisation and memory (in progress)

| # | Plate | Done when |
| --- | --- | --- |
| 25 | **Downloads folder preference** | ✅ User-configurable `downloads_folder` for organise/list journeys |
| 26 | **Save-note journey** | ✅ Notes folder preference + planner journey to write a local note |
| 27 | **Local memory export** | ✅ Export encrypted-memory contents as JSON (CLI + desktop) |

### P9 — Stage 3 diagnostics, developer tools, and CI

| # | Plate | Done when |
| --- | --- | --- |
| 28 | **Largest-folder disk journey** | ✅ Read-only ranking of top-level folders on a drive |
| 29 | **Pytest workflow pack** | ✅ Run the current directory's pytest suite behind the broker |
| 30 | **GitHub Actions PR gates** | ✅ PRs into `main` run pytest + validate; protection how-to in CONTRIBUTING |

### P10 — Stage 3 voice polish and Windows folders

| # | Plate | Done when |
| --- | --- | --- |
| 31 | **Voice listen UX** | ✅ Desktop Voice disables while listening and shows recognition confidence |
| 32 | **Open folder in Explorer** | ✅ Open Downloads (or a named folder) in Explorer behind the broker |
| 33 | **Recycle bin inspect / empty** | ✅ Preview Recycle Bin, then empty only with hard confirmation |

### P11 — Stage 3 search, cleanup, and everyday apps

| # | Plate | Done when |
| --- | --- | --- |
| 34 | **Find files by name** | ✅ Depth-capped filename search behind the broker |
| 35 | **Temp inspect / clean** | ✅ Preview user TEMP files, then delete only with hard confirmation |
| 36 | **Everyday app launch aliases** | ✅ Chrome / Edge / VS Code (and similar) resolve on `launch_app` |

### P12 — Stage 3 organisation, clipboard, and voice

| # | Plate | Done when |
| --- | --- | --- |
| 37 | **Recent files in Downloads** | ✅ Newest-first listing behind the broker |
| 38 | **Clipboard inspect** | ✅ Type/length (optional preview); secrets withheld |
| 39 | **Opt-in spoken confirmations** | ✅ TTS read-back of plan steps; broker-gated; no always-on mic |

### P13 — Stage 3 organisation, desktop capture, and diagnostics

| # | Plate | Done when |
| --- | --- | --- |
| 40 | **Copy/move file with preview** | ✅ Preview then copy or move one file; move records undo |
| 41 | **Screenshot / window snapshot** | ✅ Capture a PNG behind the broker (screen or titled window) |
| 42 | **Network / wifi inspect** | ✅ Read-only adapter, IP, and profile listing; no secrets |

### P14 — Stage 3 clipboard notes, Downloads cleanup, and power

| # | Plate | Done when |
| --- | --- | --- |
| 43 | **Save clipboard to notes** | ✅ Clipboard text to `notes_folder`; secrets/non-text refused |
| 44 | **Empty old Downloads** | ✅ Preview top-level Downloads files older than N days, then delete only with hard confirmation |
| 45 | **Battery / power inspect** | ✅ Read-only battery charge and AC/battery status; no secrets |

### P15 — Stage 3 windows, installed browser, and devices

| # | Plate | Done when |
| --- | --- | --- |
| 46 | **Close window by title** | ✅ Send WM_CLOSE to a matching window; never taskkill / Stop-Process |
| 47 | **Open URL in Chrome/Edge** | ✅ Start-Process the installed browser with an http(s) URL (not Playwright) |
| 48 | **Printer inspect** | ✅ Read-only default/list printers; no job contents or secrets |

### P16 — Stage 3 organisation, startup, and default browser

| # | Plate | Done when |
| --- | --- | --- |
| 49 | **Recent files in Documents** | ✅ Newest-first listing behind the broker (same caps as Downloads) |
| 50 | **Startup apps inspect** | ✅ Read-only HKCU/HKLM Run + Startup folder listing; no enable/disable |
| 51 | **Default browser inspect** | ✅ Read-only UserChoice ProgId for http(s); no association changes |

### P17 — Stage 3 display, Windows Update, and locale

| # | Plate | Done when |
| --- | --- | --- |
| 52 | **Display / resolution inspect** | ✅ Read-only attached displays and resolutions; no mode changes |
| 53 | **Windows Update last-install date** | ✅ Read-only last hotfix install date; does not install updates |
| 54 | **Time zone / locale inspect** | ✅ Read-only timezone and culture; no tzutil / Set-Culture |

### P18 — Stage 3 organisation, workday, and theme

| # | Plate | Done when |
| --- | --- | --- |
| 55 | **Screenshots folder preference** | ✅ User-configurable `screenshots_folder` for the capture journey |
| 56 | **Open workday folder in Explorer** | Named journey lists then opens the workday folder (not the full start-workday ritual) |
| 57 | **Dark/light theme inspect** | Read-only AppsUseLightTheme / SystemUsesLightTheme; no theme writes |

## Non-negotiables (do not drift)

1. Models propose; the **broker** disposes.
2. Adapters never run without broker authorisation.
3. Financial / credential / destructive steps always need **fresh hard confirmation**.
4. Dry-run / preview is preferred before side effects.
5. Personal memory stays **local-first** and encrypted at rest.
6. Browser page content is **untrusted data** — never auto-executed as tools.
7. No unsupervised “do anything” mode. Trust is per routine, not global.

Anything that weakens these does not ship.

---

## Build order (source of truth)

Work top-down. Finish a plate before starting the next unless a dependency forces a small parallel spike.

### P0 — make Arbora testable by someone else

| # | Plate | Done when |
| --- | --- | --- |
| 1 | **Packaging + first-run** | ✅ Private tester path: `scripts/first_run.ps1` + Setup checklist |
| 2 | **`arbora doctor`** | ✅ `arbora doctor` (+ `--json`) with shared probe fix hints |
| 3 | **Trust UX** | ✅ UI dialogs: inspect/revoke routines + session audit |
| 4 | **Emergency stop** | ✅ Broker halt between steps + desktop Stop button |

### P1 — make the three journeys feel real

| # | Plate | Done when |
| --- | --- | --- |
| 5 | **Journey hardening** | ✅ Clearer workday / diagnose / research templates + broader matchers |
| 6 | **Richer browser (broker-gated)** | ✅ `click` / `type_text` / `wait_for` / `snapshot` behind the broker |
| 7 | **File undo where feasible** | ✅ `apply_organise` + `undo_last_organise` with local journal |

### P2 — close the MVP capability gaps

| # | Plate | Done when |
| --- | --- | --- |
| 8 | **Opt-in cloud provider** | ✅ OpenAI-compatible provider + privacy banner when selected |
| 9 | **Reusable workflow packs** | ✅ JSON packs in `workflows/` + `~/.arbora/workflows/` |
| 10 | **Scheduled trusted routines** | ✅ Optional daily time triggers for *already trusted* routines only — never free-form unsupervised loops |

### P3 — MVP polish (after P2)

| # | Plate | Done when |
| --- | --- | --- |
| 11 | **Persistent audit log** | ✅ Audit events survive restarts in encrypted local memory |
| 12 | **Desktop schedule UX** | ✅ Manage trusted-routine schedules from `arbora-ui` |

---

## Explicitly later (do not start now)

Keep these out of the current queue unless the safety or MVP bar requires them:

- calendar / email / cloud-storage suites;
- mobile remote desktop control;
- multi-user / team admin;
- smart-home / IoT;
- macOS / Linux feature parity;
- always-on chat agent with broad system rights;
- marketplace / community plugin ecosystem (after the broker contract is stable).

The long-term stage list in the root README still applies; this file only prioritises the **next** stretch.

---

## MVP definition of done (exit criteria)

An early tester on a clean Windows install of Arbora can:

1. complete a workday setup routine after one guided approval;
2. run a read-only PC diagnostic and approve a safe repair plan;
3. set up a sample developer project through chat;
4. inspect the audit log and revoke a trusted routine;
5. keep personal memory local with cloud models disabled.

When those five hold without heroic setup, Stage 2 MVP is met. Then revisit Stage 3 (personal depth) in the root README.

---

## How to use this file in practice

- Pick the **lowest unfinished P0/P1 plate** unless blocked.
- Land meaningful work with a numbered `documentation/NNN-*.md` entry as usual.
- After a plate ships, mark it done here (or strike the row) and refresh “Current position”.
- Do not add shiny side quests above unfinished P0 items.

---

## Suggested next plate

P18 plate 55 is done. Next: open the workday folder in Explorer as a named journey, then dark/light theme inspect.
