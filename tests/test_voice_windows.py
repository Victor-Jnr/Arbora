"""Regression tests for Windows voice input helpers."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from arbora.voice.windows import listen_once, voice_input_available


def test_voice_input_available_on_windows():
    with patch("arbora.voice.windows.sys.platform", "win32"):
        assert voice_input_available() is True


def test_listen_once_success():
    fake = type("P", (), {"returncode": 0, "stdout": "start my workday\n", "stderr": ""})()
    with patch("arbora.voice.windows.sys.platform", "win32"), patch(
        "arbora.voice.windows.subprocess.run", return_value=fake
    ):
        result = listen_once()
    assert result.ok is True
    assert result.text == "start my workday"
    assert result.confidence is None


def test_listen_once_parses_confidence():
    fake = type("P", (), {"returncode": 0, "stdout": "CONFIDENCE=0.82\nlist downloads\n", "stderr": ""})()
    with patch("arbora.voice.windows.sys.platform", "win32"), patch(
        "arbora.voice.windows.subprocess.run", return_value=fake
    ) as run:
        result = listen_once()
    assert result.ok is True
    assert result.text == "list downloads"
    assert result.confidence == pytest.approx(0.82)
    script = run.call_args.args[0][-1]
    assert "CurrentUICulture" in script
    assert "InitialSilenceTimeout" in script


def test_listen_once_no_speech():
    fake = type("P", (), {"returncode": 2, "stdout": "", "stderr": ""})()
    with patch("arbora.voice.windows.sys.platform", "win32"), patch(
        "arbora.voice.windows.subprocess.run", return_value=fake
    ):
        result = listen_once()
    assert result.ok is False
    assert result.error == "No speech detected."


def test_listen_once_non_windows():
    with patch("arbora.voice.windows.sys.platform", "linux"):
        result = listen_once()
    assert result.ok is False
    assert "Windows-only" in (result.error or "")
