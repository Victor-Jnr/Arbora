"""Local stub provider used until a real model runtime is wired."""

from __future__ import annotations


class EchoProvider:
    """Deterministic stand-in that never leaves the machine."""

    name = "echo-local"

    def complete(self, prompt: str) -> str:
        return (
            "[echo-local] No model configured. Arbora is using the rule-based planner stub.\n"
            f"Prompt received ({len(prompt)} chars)."
        )
