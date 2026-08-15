"""Regression tests for arbora validate."""

from __future__ import annotations

from pathlib import Path

from arbora.cli.validate import run_mvp_checks, run_validate


def test_run_mvp_checks_all_pass(tmp_path: Path):
    checks = run_mvp_checks(memory_root=tmp_path)
    assert len(checks) == 5
    assert all(check.ok for check in checks), [check for check in checks if not check.ok]


def test_validate_cli_json(tmp_path: Path, capsys):
    code = run_validate(["--json", "--memory-dir", str(tmp_path)])
    assert code == 0
    out = capsys.readouterr().out
    assert '"workday_journey"' in out
    assert '"ok": true' in out
