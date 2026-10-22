"""Extrahiert genau eine Aktion (oder FERTIG) aus einer Modellantwort.

Der KI-Modus schreibt gern Markdown, Quellenhinweise oder Zusatztext um den
eigentlichen Block. Text vor dem Block und nach `ENDE` wird ignoriert.
Ist der Block selbst kaputt, wird `FormatFehler` geworfen – geraten wird nicht.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_SCHLUESSELZEILE = re.compile(r"^[\s*_>`]*(GEDANKE|AKTION|EINGABE|FERTIG)[*_`]*\s*:[*_`]*\s?(.*)$")
_ENDEZEILE = re.compile(r"^[\s*_>`]*ENDE[\s*_`.]*$")
_CODEZAUN = re.compile(r"^\s*(```|~~~)")
_UNSICHTBAR = str.maketrans({" ": " ", "​": None, "‌": None, "﻿": None})


class FormatFehler(ValueError):
    """Die Antwort entspricht nicht dem Aktionsformat."""


@dataclass(frozen=True)
class Aktion:
    gedanke: str
    werkzeug: str
    eingabe: str

    def als_block(self) -> str:
        return (
            f"GEDANKE: {self.gedanke}\nAKTION: {self.werkzeug}\n"
            f"EINGABE:\n```\n{self.eingabe}\n```\nENDE"
        )


@dataclass(frozen=True)
class Fertig:
    bericht: str

    def als_block(self) -> str:
        return f"FERTIG:\n{self.bericht}\nENDE"


def parse_antwort(text: str) -> Aktion | Fertig:
    zeilen = text.translate(_UNSICHTBAR).replace("\r\n", "\n").split("\n")
    start = _finde_start(zeilen)
    schluessel, _ = _schluessel(zeilen[start])
    if schluessel == "FERTIG":
        ergebnis: Aktion | Fertig
        ergebnis, ende = _parse_fertig(zeilen, start)
    else:
        ergebnis, ende = _parse_aktion(zeilen, start)
    _pruefe_rest(zeilen[ende + 1 :])
    return ergebnis


def _schluessel(zeile: str) -> tuple[str | None, str]:
    if _ENDEZEILE.match(zeile):
        return "ENDE", ""
    treffer = _SCHLUESSELZEILE.match(zeile)
    if treffer is None:
        return None, ""
    return treffer.group(1), treffer.group(2).strip()


def _finde_start(zeilen: list[str]) -> int:
    for index, zeile in enumerate(zeilen):
        if _schluessel(zeile)[0] in ("GEDANKE", "AKTION", "FERTIG"):
            return index
    raise FormatFehler("Kein Block gefunden: Es fehlt GEDANKE/AKTION oder FERTIG.")


def _finde_ende(zeilen: list[str], ab: int) -> int:
    for index in range(ab, len(zeilen)):
        if _schluessel(zeilen[index])[0] == "ENDE":
            return index
    raise FormatFehler("Die abschließende Zeile ENDE fehlt.")


def _parse_fertig(zeilen: list[str], start: int) -> tuple[Fertig, int]:
    _, rest = _schluessel(zeilen[start])
    ende = _finde_ende(zeilen, start + 1)
    bericht = _bereinige([rest, *zeilen[start + 1 : ende]])
    return Fertig(bericht=bericht), ende


def _parse_aktion(zeilen: list[str], start: int) -> tuple[Aktion, int]:
    gedanke_zeilen: list[str] = []
    index = start
    schluessel, rest = _schluessel(zeilen[index])
    if schluessel == "GEDANKE":
        gedanke_zeilen.append(rest)
        index += 1
        while index < len(zeilen):
            schluessel, rest = _schluessel(zeilen[index])
            if schluessel == "AKTION":
                break
            if schluessel is not None:
                raise FormatFehler(f"Nach GEDANKE wurde AKTION erwartet, nicht {schluessel}.")
            gedanke_zeilen.append(zeilen[index])
            index += 1
        else:
            raise FormatFehler("Die Zeile AKTION fehlt.")

    werkzeug = rest.strip("*_` ").lower()
    if not werkzeug:
        raise FormatFehler("Nach AKTION: fehlt der Werkzeugname.")

    eingabe_index, eingabe_rest = _finde_eingabe(zeilen, index + 1)
    ende = _finde_ende(zeilen, eingabe_index + 1)
    eingabe = _bereinige_eingabe([eingabe_rest, *zeilen[eingabe_index + 1 : ende]])
    gedanke = _bereinige(gedanke_zeilen)
    return Aktion(gedanke=gedanke, werkzeug=werkzeug, eingabe=eingabe), ende


def _finde_eingabe(zeilen: list[str], ab: int) -> tuple[int, str]:
    """Sucht die EINGABE-Zeile; Fremdtext (z. B. Quellen) davor wird übersprungen."""
    for index in range(ab, len(zeilen)):
        schluessel, rest = _schluessel(zeilen[index])
        if schluessel == "EINGABE":
            return index, rest
        if schluessel is not None:
            raise FormatFehler(f"Nach AKTION wurde EINGABE erwartet, nicht {schluessel}.")
    raise FormatFehler("Die Zeile EINGABE fehlt.")


def _pruefe_rest(zeilen: list[str]) -> None:
    for zeile in zeilen:
        if _schluessel(zeile)[0] in ("AKTION", "FERTIG"):
            raise FormatFehler("Mehr als ein Block in der Antwort – bitte genau eine Aktion.")


def _bereinige(zeilen: list[str]) -> str:
    return "\n".join(zeilen).strip()


def _bereinige_eingabe(zeilen: list[str]) -> str:
    """Entfernt Leerzeilen und Markdown-Codezäune am Rand, nicht im Inneren."""
    while zeilen and not zeilen[0].strip():
        zeilen = zeilen[1:]
    while zeilen and not zeilen[-1].strip():
        zeilen = zeilen[:-1]
    if zeilen and _CODEZAUN.match(zeilen[0]):
        zeilen = zeilen[1:]
    if zeilen and _CODEZAUN.match(zeilen[-1]):
        zeilen = zeilen[:-1]
    return "\n".join(zeilen).strip("\n")
