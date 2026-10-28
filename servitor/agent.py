"""Agenten-Schleife: Prompt bauen, Modell fragen, Antwort parsen, Werkzeug ausführen."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from servitor.config import Config
from servitor.llm import BackendBlockiert, BackendFehler, LLMBackend
from servitor.parser import Aktion, Fertig, FormatFehler, parse_antwort
from servitor.prompts import korrekturanfrage, systemprompt
from servitor.tools import Werkzeug

logger = logging.getLogger(__name__)

KURZ_ZEICHEN = 300
GEKUERZT = " […gekürzt]"
MAX_FRUEHERE_AUFGABEN = 5


class Status(Enum):
    FERTIG = "fertig"
    MAX_SCHRITTE = "max_schritte"
    ZU_VIELE_FEHLER = "zu_viele_fehler"
    BACKEND_FEHLER = "backend_fehler"
    BLOCKIERT = "blockiert"


@dataclass(frozen=True)
class Ergebnis:
    status: Status
    text: str
    schritte: int


@dataclass(frozen=True)
class Runde:
    antwort: str
    rueckmeldung: str

    def als_text(self, nummer: int) -> str:
        return (
            f"--- Runde {nummer} ---\n"
            f"DEINE ANTWORT:\n{self.antwort}\n"
            f"ERGEBNIS:\n{self.rueckmeldung}"
        )


class Beobachter:
    """Wird über den Fortschritt informiert. Standardmäßig passiert nichts."""

    def bei_aktion(self, schritt: int, aktion: Aktion) -> None: ...

    def bei_ergebnis(self, ergebnis: str) -> None: ...

    def bei_formatfehler(self, fehler: str) -> None: ...


class Agent:
    def __init__(
        self,
        backend: LLMBackend,
        werkzeuge: dict[str, Werkzeug],
        config: Config,
        ketzer: bool = False,
        beobachter: Beobachter | None = None,
    ) -> None:
        self._backend = backend
        self._werkzeuge = werkzeuge
        self._config = config
        self._systemprompt = systemprompt(werkzeuge.values(), ketzer=ketzer)
        self._beobachter = beobachter or Beobachter()
        self._verlauf: list[Runde] = []
        self._fruehere: list[tuple[str, Ergebnis]] = []

    def ausfuehren(self, aufgabe: str) -> Ergebnis:
        """Bearbeitet eine Aufgabe. Frühere Aufgaben dieser Sitzung stehen als Kontext im Prompt."""
        ergebnis = self._bearbeite(aufgabe)
        self._fruehere.append((aufgabe, ergebnis))
        return ergebnis

    def vergessen(self) -> None:
        """Löscht den Kontext früherer Aufgaben (neues Gespräch)."""
        self._fruehere = []

    def _bearbeite(self, aufgabe: str) -> Ergebnis:
        self._verlauf = []
        fehler_in_folge = 0
        for schritt in range(1, self._config.max_schritte + 1):
            try:
                antwort = self._backend.frage(self.baue_prompt(aufgabe))
            except BackendFehler as fehler:
                return _backend_abbruch(fehler, schritt)

            try:
                geparst = parse_antwort(antwort)
            except FormatFehler as fehler:
                logger.warning("Formatfehler in Schritt %d: %s", schritt, fehler)
                self._beobachter.bei_formatfehler(str(fehler))
                self._verlauf.append(Runde(_kuerze(antwort, 500), korrekturanfrage(str(fehler))))
                fehler_in_folge += 1
            else:
                if isinstance(geparst, Fertig):
                    return Ergebnis(Status.FERTIG, geparst.bericht, schritt)
                ok = self._fuehre_aus(schritt, geparst)
                fehler_in_folge = 0 if ok else fehler_in_folge + 1

            if fehler_in_folge >= self._config.max_fehler_in_folge:
                return Ergebnis(
                    Status.ZU_VIELE_FEHLER,
                    f"{fehler_in_folge} unbrauchbare Antworten in Folge.",
                    schritt,
                )
        return Ergebnis(
            Status.MAX_SCHRITTE,
            f"Nach {self._config.max_schritte} Schritten nicht fertig geworden.",
            self._config.max_schritte,
        )

    def _fuehre_aus(self, schritt: int, aktion: Aktion) -> bool:
        """Führt die Aktion aus und merkt sie sich. False bei unbekanntem Werkzeug."""
        self._beobachter.bei_aktion(schritt, aktion)
        werkzeug = self._werkzeuge.get(aktion.werkzeug)
        if werkzeug is None:
            namen = ", ".join(self._werkzeuge)
            rueckmeldung = f"FEHLER: Unbekanntes Werkzeug '{aktion.werkzeug}'. Erlaubt: {namen}"
        else:
            rueckmeldung = werkzeug.ausfuehren(aktion.eingabe)
        self._beobachter.bei_ergebnis(rueckmeldung)
        self._verlauf.append(Runde(aktion.als_block(), rueckmeldung))
        return werkzeug is not None

    def baue_prompt(self, aufgabe: str) -> str:
        kopf = (
            f"{self._systemprompt}\n\n{self._fruehere_als_text()}"
            f"AUFGABE\n{aufgabe}\n\nBISHERIGER VERLAUF\n"
        )
        fuss = "\n\nDeine nächste Antwort (genau ein Block):"
        budget = self._config.max_prompt_zeichen - len(kopf) - len(fuss)
        runden = [r.als_text(i) for i, r in enumerate(self._verlauf, start=1)]
        verlauf = "\n\n".join(kuerze_verlauf(runden, budget)) or "(noch nichts)"
        return kopf + verlauf + fuss

    def _fruehere_als_text(self) -> str:
        if not self._fruehere:
            return ""
        eintraege = [
            f"- Aufgabe: {_kuerze(aufgabe, KURZ_ZEICHEN)}\n"
            f"  Ergebnis ({ergebnis.status.value}): {_kuerze(ergebnis.text, KURZ_ZEICHEN)}"
            for aufgabe, ergebnis in self._fruehere[-MAX_FRUEHERE_AUFGABEN:]
        ]
        return "FRÜHERE AUFGABEN IN DIESER SITZUNG\n" + "\n".join(eintraege) + "\n\n"


def kuerze_verlauf(runden: list[str], budget: int) -> list[str]:
    """Kürzt erst ältere Runden, entfernt sie dann; die neueste Runde bleibt erhalten."""
    ergebnis = list(runden)
    for index in range(len(ergebnis) - 1):
        if _laenge(ergebnis) <= budget:
            return ergebnis
        ergebnis[index] = _kuerze(ergebnis[index], KURZ_ZEICHEN)

    entfernt = 0
    while _laenge(ergebnis) > budget and len(ergebnis) > 1:
        ergebnis.pop(0)
        entfernt += 1
    if entfernt:
        ergebnis.insert(0, f"[{entfernt} ältere Runde(n) entfernt]")
    if ergebnis and _laenge(ergebnis) > budget:
        ergebnis[-1] = _kuerze(ergebnis[-1], max(0, budget - _laenge(ergebnis[:-1]) - 2))
    return ergebnis


def _laenge(teile: list[str]) -> int:
    return len("\n\n".join(teile))


def _kuerze(text: str, max_zeichen: int) -> str:
    if len(text) <= max_zeichen:
        return text
    return text[: max(0, max_zeichen - len(GEKUERZT))] + GEKUERZT


def _backend_abbruch(fehler: BackendFehler, schritt: int) -> Ergebnis:
    status = Status.BLOCKIERT if isinstance(fehler, BackendBlockiert) else Status.BACKEND_FEHLER
    logger.error("Backend-Fehler in Schritt %d: %s", schritt, fehler)
    return Ergebnis(status, str(fehler), schritt)
