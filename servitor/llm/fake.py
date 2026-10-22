"""Fake-Backend für Tests: liefert vorbereitete Antworten der Reihe nach."""

from __future__ import annotations

from collections.abc import Iterable

from servitor.llm import BackendFehler


class FakeBackend:
    def __init__(self, antworten: Iterable[str | BackendFehler]) -> None:
        self._antworten = list(antworten)
        self.prompts: list[str] = []

    def frage(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self._antworten:
            raise BackendFehler("Das Fake-Backend hat keine Antworten mehr.")
        antwort = self._antworten.pop(0)
        if isinstance(antwort, BackendFehler):
            raise antwort
        return antwort
