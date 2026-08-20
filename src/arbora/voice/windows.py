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
    confidence: float | None = None


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
$culture = [System.Globalization.CultureInfo]::CurrentUICulture
try {{
  $engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine($culture)
}} catch {{
  $engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine
}}
$engine.SetInputToDefaultAudioDevice()
$engine.InitialSilenceTimeout = [TimeSpan]::FromSeconds(4)
$engine.BabbleTimeout = [TimeSpan]::FromSeconds(4)
$engine.EndSilenceTimeout = [TimeSpan]::FromSeconds(1.5)
$grammar = New-Object System.Speech.Recognition.DictationGrammar
$engine.LoadGrammar($grammar)
$result = $engine.Recognize([TimeSpan]::FromSeconds({timeout_seconds}))
if ($null -eq $result) {{ exit 2 }}
Write-Output ("CONFIDENCE=" + $result.Confidence)
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
    return _parse_listen_stdout(proc.stdout)


def _parse_listen_stdout(stdout: str) -> VoiceResult:
    lines = [line.strip() for line in (stdout or "").splitlines() if line.strip()]
    confidence: float | None = None
    text_lines = lines
    if lines and lines[0].upper().startswith("CONFIDENCE="):
        raw = lines[0].split("=", 1)[1].strip()
        try:
            confidence = float(raw)
        except ValueError:
            confidence = None
        text_lines = lines[1:]
    text = " ".join(text_lines).strip()
    if not text:
        return VoiceResult(False, error="No speech detected.")
    return VoiceResult(True, text=text, confidence=confidence)
