"""Tool adapters for Windows surfaces (desktop, files, terminal)."""

from arbora.adapters.desktop import DesktopAdapter
from arbora.adapters.files import FilesAdapter
from arbora.adapters.terminal import TerminalAdapter

__all__ = ["DesktopAdapter", "FilesAdapter", "TerminalAdapter"]
