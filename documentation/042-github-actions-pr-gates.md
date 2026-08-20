# 042 — GitHub Actions PR gates

- **Date:** 2026-08-19
- **Commit subject:** Gate pull requests to main with pytest and arbora validate
- **Stage:** Stage 3

## Summary

The CI workflow already ran pytest on PRs, but it did not block a merge by itself and did not run `arbora validate`. CI now cancels stale runs, runs pytest plus validate as **pytest (Windows)**, and CONTRIBUTING documents the one-time GitHub branch-protection click that actually prevents merging red PRs.

## Changes

- `.github/workflows/ci.yml`: concurrency, `workflow_dispatch`, `arbora validate` after pytest
- `.github/pull_request_template.md`: test plan + safety checklist
- README CI badge
- CONTRIBUTING: PR into `main`, require **pytest (Windows)**
- Test that the workflow file still mentions `pull_request`, `main`, pytest, and validate

## Safety / permissions

- Workflow `contents: read` only
- No secrets, no PyPI publish
- Playwright Chromium is not installed on the runner; browser tests stay mocked

## How to verify

```powershell
pytest tests/test_ci_workflow.py
```

After this lands on `main`: GitHub → Settings → Branches → protect `main` → require **pytest (Windows)**. Open a pull request and confirm the check runs before merge.
