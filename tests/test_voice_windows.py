"""Regression tests for Windows voice input helpers."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from arbora.voice.windows import listen_once, sanitize_speech_text, speak_text, voice_input_available, voice_output_available


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


def test_sanitize_speech_text_collapses_and_caps():
    assert sanitize_speech_text("  hello   world  ") == "hello world"
    out = sanitize_speech_text("a" * 500)
    assert out.endswith("…")
    assert len(out) == 401


def test_speak_text_uses_synthesizer_not_microphone():
    fake = type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    with patch("arbora.voice.windows.sys.platform", "win32"), patch(
        "arbora.voice.windows.subprocess.run", return_value=fake
    ) as run:
        result = speak_text("Please review the plan.")
    assert result.ok is True
    assert result.text == "Please review the plan."
    script = run.call_args.args[0][-1]
    assert "SpeechSynthesizer" in script
    assert "SetInputToDefaultAudioDevice" not in script
    assert "SpeechRecognitionEngine" not in script


def test_speak_text_empty_and_non_windows():
    with patch("arbora.voice.windows.sys.platform", "win32"):
        empty = speak_text("   ")
    assert empty.ok is False
    with patch("arbora.voice.windows.sys.platform", "linux"):
        result = speak_text("hello")
    assert result.ok is False
    assert "Windows-only" in (result.error or "")
    assert voice_output_available() in {True, False}
