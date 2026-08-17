"""Regression tests for Windows voice input helpers."""

from __future__ import annotations

from unittest.mock import patch

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
