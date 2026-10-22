"""Werkzeuge des Agenten. Alle arbeiten nur innerhalb des Workspace."""

from __future__ import annotations

from functools import partial
from pathlib import Path

from servitor.tools.basis import Werkzeug
from servitor.tools.befehl import Bestaetigung, befehl_ausfuehren
from servitor.tools.dateien import datei_lesen, datei_schreiben, dateien_listen

__all__ = ["Bestaetigung", "Werkzeug", "erzeuge_werkzeuge"]


def erzeuge_werkzeuge(
    workspace: Path,
    bestaetigen: Bestaetigung,
    befehl_timeout: float = 60.0,
    immer_fragen: bool = True,
) -> dict[str, Werkzeug]:
    """Baut alle Werkzeuge, gebunden an den Workspace.

    `immer_fragen=False` entspricht `--auto`: Dann werden nur noch riskante
    Befehle bestätigt – diese aber immer.
    """
    werkzeuge = [
        Werkzeug(
            "datei_lesen",
            "Liest eine Datei. Eingabe: Pfad. Liefert max. 20.000 Zeichen.",
            partial(datei_lesen, workspace=workspace),
        ),
        Werkzeug(
            "datei_schreiben",
            "Legt eine Datei an oder überschreibt sie. "
            "Eingabe: erste Zeile Pfad, dann eine Leerzeile, dann der komplette Inhalt.",
            partial(datei_schreiben, workspace=workspace),
        ),
        Werkzeug(
            "dateien_listen",
            "Listet ein Verzeichnis auf. Eingabe: Pfad (optional, Standard '.').",
            partial(dateien_listen, workspace=workspace),
        ),
        Werkzeug(
            "befehl",
            f"Führt einen Shell-Befehl im Arbeitsbereich aus (Timeout {befehl_timeout:g} s). "
            "Eingabe: der Befehl. Liefert Exit-Code, stdout und stderr.",
            partial(
                befehl_ausfuehren,
                workspace=workspace,
                timeout=befehl_timeout,
                bestaetigen=bestaetigen,
                immer_fragen=immer_fragen,
            ),
        ),
    ]
    return {w.name: w for w in werkzeuge}
