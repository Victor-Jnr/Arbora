# 053 — Screenshot / window snapshot

- **Date:** 2026-08-24
- **Commit subject:** Capture a screen or window PNG behind the broker
- **Stage:** Stage 3

## Summary

Testers can ask Arbora to capture the primary screen or a titled window to a PNG under the notes screenshots folder. The write still goes through the permission broker.

## Changes

- Desktop adapter action `capture_screenshot` (`path`, optional `window_title`)
- Planner journey for “take a screenshot” / “screenshot of notepad”
- Bundled workflow pack `take-screenshot`

## Safety / permissions

- Capture is `mutate` — broker approval, not hard confirmation
- Dry-run reports the path and does not grab pixels
- Does not upload the image; window capture is title-match only

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k screenshot
arbora --provider echo --goal "take a screenshot"
```
