"""Provider-agnostic model interface."""

from __future__ import annotations

from typing import Protocol


class ModelProvider(Protocol):
    """Interchangeable local/cloud inference backend."""

    name: str

    def complete(self, prompt: str) -> str:
        """Return a completion for the given prompt."""
        ...
