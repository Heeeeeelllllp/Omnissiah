"""Schnittstelle zum Sprachmodell."""

from __future__ import annotations

from typing import Protocol


class LLMBackend(Protocol):
    def frage(self, prompt: str) -> str: ...


class BackendFehler(RuntimeError):
    """Das Backend konnte keine Antwort liefern (z. B. Timeout)."""


class BackendBlockiert(BackendFehler):
    """Google zeigt ein CAPTCHA oder blockiert die Anfrage. Nicht umgehen – abbrechen."""
