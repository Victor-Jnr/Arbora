"""Regression tests for local memory JSON export."""

from __future__ import annotations

import json
from pathlib import Path

from arbora.cli.memory_cmd import run_memory
from arbora.cli.session import build_runtime
from arbora.memory.store import export_memory_payload, memory_status_rows


def test_export_memory_payload_excludes_key_files(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    runtime.memory.set("demo", "value")
    payload = export_memory_payload(runtime.memory)
    assert payload["version"] == 1
    assert "exported_at" in payload
    assert payload["data"]["demo"] == "value"
    assert "demo" in payload["keys"]
    blob = json.dumps(payload)
    assert "key.bin" not in blob
    assert "key.dpapi" not in blob
    assert "demo" in blob


def test_memory_export_cli_stdout(tmp_path: Path, capsys):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    runtime.memory.set("marker", 1)
    code = run_memory(["--memory-dir", str(tmp_path), "export"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["marker"] == 1


def test_memory_export_cli_to_file(tmp_path: Path, capsys):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    runtime.memory.set("marker", "ok")
    out_path = tmp_path / "memory.json"
    code = run_memory(["--memory-dir", str(tmp_path), "export", "--out", str(out_path)])
    assert code == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["data"]["marker"] == "ok"
    assert "Wrote" in capsys.readouterr().out


def test_memory_status_cli(tmp_path: Path, capsys):
    build_runtime(memory_root=tmp_path, provider="echo")
    code = run_memory(["--memory-dir", str(tmp_path), "status"])
    assert code == 0
    out = capsys.readouterr().out
    assert "encrypted_at_rest" in out
    assert "key_backend" in out


def test_memory_status_rows(tmp_path: Path):
    runtime = build_runtime(memory_root=tmp_path, provider="echo")
    rows = "\n".join(memory_status_rows(runtime.memory))
    assert str(tmp_path) in rows
    assert "key_backend" in rows


def test_main_dispatches_memory():
    from unittest.mock import patch

    from arbora.cli.main import main

    with patch("arbora.cli.memory_cmd.run_memory", return_value=0) as memory:
        assert main(["memory", "export"]) == 0
        memory.assert_called_once_with(["export"])
