"""Guardrails that GitHub Actions still gates pull requests into main."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github" / "workflows" / "ci.yml"


def test_ci_runs_on_pull_requests_to_main():
    text = CI.read_text(encoding="utf-8")
    assert "pull_request:" in text
    assert "main" in text
    assert "pytest" in text
    assert "validate" in text
    assert "cancel-in-progress: true" in text
