"""Windows speech-to-text via System.Speech (no extra pip dependencies)."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceResult:
    ok: bool
    text: str = ""
    error: str | None = None


def voice_input_available() -> bool:
    return sys.platform == "win32"


def listen_once(timeout_seconds: int = 8) -> VoiceResult:
    """Listen for one dictation phrase using the default Windows microphone."""
    if not voice_input_available():
        return VoiceResult(False, error="Voice input is Windows-only in this prototype.")

    timeout_seconds = max(3, min(timeout_seconds, 30))
    script = f"""
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech
$engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine
$engine.SetInputToDefaultAudioDevice()
$grammar = New-Object System.Speech.Recognition.DictationGrammar
$engine.LoadGrammar($grammar)
$result = $engine.Recognize([TimeSpan]::FromSeconds({timeout_seconds}))
if ($null -eq $result) {{ exit 2 }}
Write-Output $result.Text
"""
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=timeout_seconds + 20,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return VoiceResult(False, error="Voice recognition timed out.")
    except OSError as exc:
        return VoiceResult(False, error=str(exc))

    if proc.returncode == 2:
        return VoiceResult(False, error="No speech detected.")
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "Voice recognition failed").strip()
        return VoiceResult(False, error=err)
    text = proc.stdout.strip()
    if not text:
        return VoiceResult(False, error="No speech detected.")
    return VoiceResult(True, text=text)
