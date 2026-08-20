# 039 — GitHub Actions pytest CI

- **Date:** 2026-08-19
- **Commit subject:** Run pytest on GitHub Actions for main and dev
- **Stage:** Stage 3

## Summary

Pushes and pull requests to `main` and `dev` now run the same Windows install path testers use (`pip install -e ".[dev]"` then `pytest`). A red check means the branch should not merge until tests pass. CI does not block `git push`; branch protection on GitHub does that.

## Changes

- Added `.github/workflows/ci.yml` (Windows, Python 3.11, pytest)
- Documented `main` / `dev` / feature-branch workflow in `CONTRIBUTING.md`

## Safety / permissions

- None — tests only; no PyPI publish, no secrets, workflow `contents: read`
- Playwright Chromium is not installed on the runner; browser tests stay mocked

## How to verify

- Open the pull request → **Checks** → **pytest (Windows)** should run
- After merge: **Actions** tab on GitHub should list **CI**
- Local equivalent: `pip install -e ".[dev]"` then `pytest`
