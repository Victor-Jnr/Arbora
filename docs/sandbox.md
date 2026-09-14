# Sandbox auto-execute (`arbora serve`)

**Audience:** testers and integrators running Arbora on an isolated Windows host (lab VM, throwaway profile, or a dedicated automation box).  
**Related:** [install.md](install.md), [prototype.md](prototype.md), localhost API change history in [084](../documentation/084-localhost-plan-accept-api.md) and [088](../documentation/088-sandbox-auto-execute.md).

This page is the operator guide for **sandbox auto-execute**: a one-shot HTTP call that plans a goal and runs **non-hard** steps without a second approve request. It is **off by default**. The permission broker still authorises every adapter call.

---

## 1. Which serve mode you want

| Mode | How you start it | What callers do | Use when |
| --- | --- | --- | --- |
| **Default plan-accept** | `arbora serve` | `POST /v1/goals` then `POST /v1/plans/{id}/approve` | A person (or UI) should inspect the plan before anything runs |
| **Sandbox auto-execute** | `arbora serve --sandbox-auto-execute` | `POST /v1/execute` | Another **local** process already decided the goal may run on this isolated box |
| **Interactive CLI** | `arbora --goal "…" --yes` | No HTTP | One-shot from a terminal; same broker rules (`--execute` for live, `--hard-yes` for hard classes) |
| **Trusted routine** | Promote after a matching plan | Repeat fingerprint skips *fresh* approve for non-hard steps | The **same** plan on a personal PC, not “run any incoming goal” |

`auto_approve` on `POST /v1/goals` is **always rejected**. Sandbox is a **separate flag and a separate route**, so a normal serve process cannot be talked into auto-running.

---

## 2. What still applies in sandbox

These do **not** turn off:

| Rule | Sandbox behaviour |
| --- | --- |
| Loopback bind | Host must be `127.0.0.1`, `localhost`, or `::1`. `0.0.0.0` is refused |
| Token | Every route, including health |
| Dry-run default | `dry_run` defaults to **true**. Live Windows side effects only when the JSON sets `"dry_run": false` |
| Hard classes | Destructive / credential / financial steps still need `"hard_confirm": true` or those steps fail |
| Broker | Adapters never run except through the permission broker |
| Halt on failure | If a step is marked to halt, later steps are skipped |

Sandbox is **not**:

- a public internet API
- a way to skip dry-run (you must pass `dry_run: false` yourself)
- a way to skip hard confirmation
- a Windows Service in Session 0 that can type into Notepad (desktop typing needs the **logged-in user**)
- the same thing as a trusted routine

---

## 3. Requirements

- Windows 10/11, Python 3.11+, Arbora installed (see [install.md](install.md))
- A **loopback** listener on this machine (`127.0.0.1:8472` by default)
- Callers on the **same** Windows host (or a tunnel you control). Arbora does not bind LAN/wildcard addresses
- Prefer a **throwaway user profile or VM** if you will set `dry_run: false`

For desktop typing / focus / Notepad, start `arbora serve` as the interactive user, not as a Session 0 service.

---

## 4. Start the sandbox server

From the repo root, with the venv active:

```powershell
.\.venv\Scripts\Activate.ps1
arbora serve --provider echo --token arbora-test-token-1 --sandbox-auto-execute
```

You should see lines similar to:

```text
Arbora plan-accept API on http://127.0.0.1:8472
POST /v1/goals then POST /v1/plans/{id}/approve  (Authorization: Bearer <token>)
SANDBOX AUTO-EXECUTE is on: POST /v1/execute plans and runs non-hard steps in one call
Hard classes still need hard_confirm. Dry-run still defaults to true.
```

Leave that window running.

### Flags and environment

| Item | Meaning |
| --- | --- |
| `--sandbox-auto-execute` | Enable `POST /v1/execute` |
| `ARBORA_SANDBOX_AUTO_EXECUTE=1` | Same as the flag (`true` / `yes` / `on` also work) |
| `--token` / `ARBORA_API_TOKEN` | Shared secret, at least 16 characters. Generated once at startup if omitted |
| `--host` | Loopback only (`127.0.0.1` default) |
| `--port` | Default `8472` |
| `--provider echo` | Offline stub planner; no Ollama required |
| `--provider ollama` | Local model (default if you omit `--provider` and prefs say ollama) |
| `--memory-dir` | Optional separate encrypted memory directory for the lab box |

Equivalent env-only enable:

```powershell
$env:ARBORA_SANDBOX_AUTO_EXECUTE = "1"
$env:ARBORA_API_TOKEN = "arbora-test-token-1"
arbora serve --provider echo
```

### Confirm it is actually on

In a **second** PowerShell window:

```powershell
$headers = @{ Authorization = "Bearer arbora-test-token-1" }
Invoke-RestMethod -Uri http://127.0.0.1:8472/v1/health -Headers $headers
```

Expect JSON that includes `"sandbox_auto_execute": true` and a `checks` array (Memory should be green). If `sandbox_auto_execute` is `false`, you started a normal serve — `POST /v1/execute` will return **403**.

Without a token, health returns **401**.

---

## 5. Call `POST /v1/execute`

One request: plan the goal, accept **non-hard** steps, run through the broker.

```powershell
$headers = @{
  Authorization = "Bearer arbora-test-token-1"
  "Content-Type" = "application/json"
}
$body = @{
  goal = "foreground window"
  dry_run = $true
  hard_confirm = $false
} | ConvertTo-Json

Invoke-RestMethod -Method POST -Uri http://127.0.0.1:8472/v1/execute -Headers $headers -Body $body
```

### Request body

| Field | Required | Default | Notes |
| --- | --- | --- | --- |
| `goal` | yes | — | Natural language, same as CLI `--goal` |
| `dry_run` | no | `true` | Set `false` only when you intend live adapter side effects |
| `hard_confirm` | no | `false` | Required for destructive / credential / financial steps |
| `auto_approve` | forbidden | — | Always **400**; use this route instead of that flag |

### Success (`200`)

The response includes the plan (so logs can show what would run), `accepted: true`, `sandbox_auto_execute: true`, and `results[]` with `ok`, `output`, `error`, `dry_run` per step.

Treat the HTTP call as successful only if **every** `results[].ok` is true. A `200` with a failed hard step is still a failed goal.

### Errors

| Status | Meaning |
| --- | --- |
| 401 | Missing or wrong token |
| 403 | Sandbox flag is off — start with `--sandbox-auto-execute` |
| 400 | Missing `goal`, `auto_approve: true`, or no approvable non-hard steps |
| 404 | Unknown path |
| 413 | Body larger than 64 KiB |

---

## 6. Dry-run vs live

| JSON | Effect |
| --- | --- |
| omit `dry_run` or `"dry_run": true` | Adapters describe what they would do. **Default. Use this first.** |
| `"dry_run": false` | Broker-authorised adapters run for real (launch apps, write files, type into windows, …) |

Example live inspect (still read-only adapters; no hard class):

```powershell
$body = @{ goal = "windows version"; dry_run = $false } | ConvertTo-Json
Invoke-RestMethod -Method POST -Uri http://127.0.0.1:8472/v1/execute -Headers $headers -Body $body
```

Do not enable live mutate goals on a machine you care about until you have watched the dry-run plan.

---

## 7. Hard confirmation

Goals such as emptying the Recycle Bin include **hard** steps. Sandbox will still plan and may run the read-only preview steps, but hard steps return `ok: false` unless you send `"hard_confirm": true`.

That is intentional. A lab flag does not collapse “empty Recycle Bin” into an ordinary mutate.

---

## 8. Useful dry-run goals

These have deterministic planner journeys (echo provider is enough):

| Goal | Typical actions |
| --- | --- |
| `foreground window` | Read-only focused window title / process |
| `windows version` | Read-only version / build |
| `pending reboot` | Read-only reboot-pending flags |
| `defender status` | Read-only Defender on/off and signature date |
| `type hello in notepad` | Launch / focus / type (halt if focus fails); dry-run does not type |

---

## 9. Other routes (unchanged)

Sandbox **does not remove** the human loop. The same process still serves:

| Method | Path | Role |
| --- | --- | --- |
| `GET` | `/v1/health` | Doctor checks + `sandbox_auto_execute` |
| `POST` | `/v1/goals` | Create a pending plan (`auto_approve` rejected) |
| `GET` | `/v1/plans/{id}` | Inspect pending plan |
| `POST` | `/v1/plans/{id}/approve` | Explicit accept |
| `GET` | `/v1/audit` | Recent audit events |
| `GET` | `/v1/routines` | Trusted routines |
| `DELETE` | `/v1/routines/{id}` | Revoke a routine |

Auth: `Authorization: Bearer <token>` or `X-Arbora-Token: <token>`.

---

## 10. Stop the server

In the serve window: `Ctrl+C`.

---

## 11. Troubleshooting

| Symptom | Check |
| --- | --- |
| `403` on `/v1/execute` | Restart with `--sandbox-auto-execute` or `ARBORA_SANDBOX_AUTO_EXECUTE=1`. Confirm health JSON. |
| `401` | Same token as `--token` / `ARBORA_API_TOKEN`. Header spelling. |
| Bind error / “loopback” | Do not pass `--host 0.0.0.0`. |
| Health Memory red | Encrypted local memory failed; see `arbora doctor`. |
| Typing / Notepad does nothing live | Serve must run in the interactive user session. Dry-run first. |
| Caller in another machine/container cannot connect | Arbora listens on loopback only. Put the caller on the same OS, or add your own local proxy — Arbora will not open a LAN port. |

---

## 12. How to verify (tests)

```powershell
pytest tests/test_api_accept.py -q
```

That suite covers missing token, `auto_approve` refusal, two-step accept, sandbox `403` when the flag is off, one-shot `/v1/execute` when the flag is on, and hard steps still needing `hard_confirm`.
