"""Smoke test for Tkinter chat module import and app construction."""

from __future__ import annotations

import tkinter as tk

from apps.desktop_chat.app import ArboraChatApp, main


def test_arbora_chat_app_constructs():
    root = tk.Tk()
    root.withdraw()
    try:
        app = ArboraChatApp(root)
        assert app._runtime is not None
        assert app.dry_run_var.get() is True
    finally:
        root.destroy()


def test_main_callable():
    assert callable(main)
