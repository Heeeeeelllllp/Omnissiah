"""Gemeinsame Bausteine der Werkzeuge: Werkzeug-Datentyp und Pfadprüfung."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


class PfadFehler(ValueError):
    """Ein Pfad zeigt aus dem Workspace heraus."""


@dataclass(frozen=True)
class Werkzeug:
    name: str
    beschreibung: str
    funktion: Callable[[str], str]

    def ausfuehren(self, eingabe: str) -> str:
        """Führt das Werkzeug aus. Wirft nie: Fehler kommen als Text zurück."""
        try:
            return self.funktion(eingabe)
        except Exception as fehler:  # noqa: BLE001 – Werkzeuge dürfen nichts nach außen werfen
            logger.exception("Werkzeug %s ist fehlgeschlagen", self.name)
            return f"FEHLER: {type(fehler).__name__}: {fehler}"


def sicherer_pfad(workspace: Path, eingabe: str) -> Path:
    """Löst einen relativen Pfad im Workspace auf und lehnt alles außerhalb ab."""
    text = eingabe.strip() or "."
    roh = Path(text)
    if roh.is_absolute():
        raise PfadFehler(f"Absolute Pfade sind nicht erlaubt: {text}")
    if ".." in roh.parts:
        raise PfadFehler(f"'..' ist in Pfaden nicht erlaubt: {text}")
    basis = workspace.resolve()
    ziel = (basis / roh).resolve()
    if not ziel.is_relative_to(basis):
        raise PfadFehler(f"Pfad zeigt aus dem Workspace heraus: {text}")
    return ziel
