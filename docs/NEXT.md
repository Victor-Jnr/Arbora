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

Stage 2 MVP capability plates in [docs/NEXT.md](docs/NEXT.md) are complete. Stage 3 work has started (see P4 below).

---

### P4 — Stage 3 personal depth (in progress)

| # | Plate | Done when |
| --- | --- | --- |
| 13 | **MVP validate CLI** | ✅ `arbora validate` dry-runs the five MVP exit criteria |
| 14 | **Opt-in user preferences** | ✅ User-set defaults in encrypted memory (`/prefs`, planner hooks) |
| 15 | **Developer project workflow pack** | Bundled dev scaffold pack + hardened setup journey |

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

**P4 #15 — Developer project workflow pack** (bundled scaffold pack + hardened setup journey).
