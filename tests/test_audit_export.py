"""Regression tests for audit export."""

from __future__ import annotations

import json
from pathlib import Path

from arbora.cli.audit_cmd import run_audit
from arbora.cli.session import build_runtime


def test_audit_export_stdout(tmp_path: Path, capsys):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    runtime.audit.record("plan_created", "export test", plan_id="p1")

    code = run_audit(["--memory-dir", str(tmp_path), "export"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert any(row["kind"] == "plan_created" for row in payload)


def test_audit_export_to_file(tmp_path: Path, capsys):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    runtime.audit.record("mvp_validate", "marker")

    out_path = tmp_path / "audit.json"
    code = run_audit(["--memory-dir", str(tmp_path), "export", "--out", str(out_path), "--limit", "5"])
    assert code == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload
    assert "Wrote" in capsys.readouterr().out
