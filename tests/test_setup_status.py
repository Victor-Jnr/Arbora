"""Tests for connection status probes and setup helpers."""

from __future__ import annotations

from unittest.mock import patch

from arbora.setup_status import Light, probe_memory, probe_ollama, probe_playwright


def test_probe_memory_green():
    status = probe_memory()
    assert status.name == "Memory"
    assert status.light == Light.GREEN


def test_probe_playwright_handles_missing_package():
    with patch.dict("sys.modules", {"playwright": None, "playwright.sync_api": None}):
        with patch("builtins.__import__", side_effect=ImportError("nope")):
            # Directly test the ImportError path by mocking the import inside the function.
            pass
    with patch("arbora.setup_status.probe_playwright", wraps=probe_playwright):
        # Call with patched import at module level used by probe
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
