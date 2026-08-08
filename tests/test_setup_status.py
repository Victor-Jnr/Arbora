"""Tests for connection status probes and setup helpers."""

from __future__ import annotations

from unittest.mock import patch

from arbora.setup_status import (
    Light,
    ServiceStatus,
    checklist_summary,
    first_run_checklist,
    fix_hint_for,
    probe_memory,
    probe_ollama,
    probe_playwright,
)


def test_probe_memory_green():
    status = probe_memory()
    assert status.name == "Memory"
    assert status.light == Light.GREEN


def test_probe_playwright_handles_missing_package():
    with patch.dict("sys.modules", {"playwright": None, "playwright.sync_api": None}):
        with patch("builtins.__import__", side_effect=ImportError("nope")):
            pass
    import arbora.setup_status as mod

    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("playwright"):
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        status = mod.probe_playwright()
    assert status.light == Light.RED
    assert "package" in status.detail.lower()


def test_probe_ollama_returns_status():
    status = probe_ollama()
    assert status.name == "Ollama"
    assert status.light in {Light.GREEN, Light.YELLOW, Light.RED}


def test_fix_hint_ready():
    status = ServiceStatus("Memory", Light.GREEN, "ok")
    assert fix_hint_for(status) == "Ready."


def test_fix_hint_ollama_missing_model():
    status = ServiceStatus("Ollama", Light.YELLOW, "up, missing model")
    assert "ollama pull" in fix_hint_for(status)


def test_first_run_checklist_shape():
    steps = first_run_checklist()
    assert [s.id for s in steps] == ["memory", "ollama", "playwright"]
    ready, partial, blocked = checklist_summary(steps)
    assert ready + partial + blocked == 3
