# Apps

Desktop surfaces for Arbora.

## Desktop chat (Tkinter)

Plan → approve → execute in a native window, sharing the same broker runtime as the CLI.

```powershell
pip install -e ".[dev]"
arbora-ui
```

Or:

```powershell
python -m apps.desktop_chat
```

Uses forest/ink chrome, provider selector (echo/ollama), dry-run toggle, trusted-routine awareness, hard-confirmation dialogs, a **Connections** corner with red/yellow/green lights (Memory / Ollama / Playwright), and **Setup** with a first-run checklist plus Chromium install.

Private testers: run `.\scripts\first_run.ps1` then `arbora-ui` (see [docs/install.md](../docs/install.md)).
