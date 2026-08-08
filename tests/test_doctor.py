"""Tests for arbora doctor CLI."""

from __future__ import annotations

from unittest.mock import patch

from arbora.cli.doctor import _exit_code, run_doctor
from arbora.setup_status import FirstRunStep, Light, ServiceStatus


def _step(name: str, light: Light, *, required: bool = True) -> FirstRunStep:
    return FirstRunStep(
        name.lower(),
        name,
        ServiceStatus(name, light, "detail"),
        required=required,
    )


def test_exit_code_green():
    assert _exit_code([_step("Memory", Light.GREEN)]) == 0


def test_exit_code_optional_yellow():
    assert (
        _exit_code(
            [
                _step("Memory", Light.GREEN, required=True),
                _step("Ollama", Light.YELLOW, required=False),
            ]
        )
        == 2
    )


def test_exit_code_optional_red_is_warning():
    assert (
        _exit_code(
            [
                _step("Memory", Light.GREEN, required=True),
                _step("Ollama", Light.RED, required=False),
            ]
        )
        == 2
    )


def test_exit_code_required_red():
    assert _exit_code([_step("Memory", Light.RED, required=True)]) == 1


def test_run_doctor_prints_and_returns(capsys):
    fake = [
        FirstRunStep(
            "memory",
            "Encrypted local memory",
            ServiceStatus("Memory", Light.GREEN, "encrypted (dpapi)"),
            required=True,
        ),
        FirstRunStep(
            "ollama",
            "Local model (Ollama)",
            ServiceStatus("Ollama", Light.YELLOW, "up, missing model"),
            required=False,
        ),
        FirstRunStep(
            "playwright",
            "Browser runtime (Playwright)",
            ServiceStatus("Playwright", Light.GREEN, "Chromium ready"),
            required=False,
        ),
    ]
    with patch("arbora.cli.doctor.first_run_checklist", return_value=fake):
        code = run_doctor([])
    out = capsys.readouterr().out
    assert "Arbora doctor" in out
    assert "[OK" in out
    assert "[WARN" in out
    assert "fix:" in out
    assert code == 2


def test_run_doctor_json(capsys):
    fake = [
        FirstRunStep(
            "memory",
            "Encrypted local memory",
            ServiceStatus("Memory", Light.GREEN, "ok"),
            required=True,
        )
    ]
    with patch("arbora.cli.doctor.first_run_checklist", return_value=fake):
        code = run_doctor(["--json"])
    out = capsys.readouterr().out
    assert '"name": "Memory"' in out
    assert code == 0


def test_main_dispatches_doctor():
    from arbora.cli.main import main

    with patch("arbora.cli.doctor.run_doctor", return_value=0) as doctor:
        assert main(["doctor"]) == 0
        doctor.assert_called_once_with([])
