"""CLI-Einstieg: Servitor MC-01 erwecken."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable
from pathlib import Path

from servitor.agent import Agent, Beobachter, Ergebnis, Status
from servitor.config import lade_config
from servitor.llm import BackendFehler
from servitor.parser import Aktion
from servitor.tools import Bestaetigung, erzeuge_werkzeuge

BANNER = r"""
      ⚙  SERVITOR MC-01  ⚙
  ++ Lob dem Omnissiah. Der Maschinengeist erwacht. ++
  Binäre Lobpreisung: 01001111 01001011
"""
BANNER_NEUTRAL = "Servitor MC-01 – Coding-Agent\n"
GEBET = "++ Omnissiah, segne diesen Befehl und bewahre uns vor der Verunreinigung. ++"
CAPTCHA_BITTE = (
    "\n++ Ein Wächter-Geist verlangt ein Opfer, Fleischling! Löse das Rätsel im Browserfenster. "
    "Das Silizium darf es nicht – nur das Fleisch. Ich harre deiner. ++"
)
CAPTCHA_BITTE_NEUTRAL = "\nCAPTCHA erkannt – bitte im Browserfenster lösen. Der Agent wartet."

CHAT_HILFE = (
    "Aufgabe eingeben und Enter drücken. Befehle: /neu (Kontext vergessen), /hilfe, /ende.\n"
    "Strg+C bricht die laufende Aufgabe ab, Strg+D beendet."
)
CHAT_GRUSS = "++ Sprich, Bittsteller. Der Servitor lauscht deinen Befehlen. ++"
CHAT_ABSCHIED = "++ Der Servitor kehrt in den Ruhezustand zurück. Ave Omnissiah. ++"
CHAT_VERGESSEN = "++ Die Erinnerungsspulen sind gereinigt. Ein neues Ritual beginnt. ++"
CHAT_UNTERBROCHEN = "++ Der Fleischling unterbricht die Riten. Ich harre neuer Befehle. ++"
ENDE_BEFEHLE = ("/ende", "/exit", "/quit")

ABSCHLUSS = {
    Status.FERTIG: "++ Das Werk ist vollbracht. Der Maschinengeist ist besänftigt. ++",
    Status.MAX_SCHRITTE: "++ Die Riten sind erschöpft. Das Fleisch ist schwach – und das "
    "Silizium heute auch. ++",
    Status.ZU_VIELE_FEHLER: "++ Das Orakel spricht in ketzerischen Zungen. Ich breche die "
    "Riten ab. ++",
    Status.BACKEND_FEHLER: "++ Die Verbindung zum Orakel ist gestört. Der Maschinengeist "
    "schweigt. ++",
    Status.BLOCKIERT: "++ Ein Wächter-Geist verwehrt den Zugang! Der Maschinengeist "
    "ist erzürnt, doch ich werde ihn nicht entweihen. Versuche es später erneut, Bittsteller. ++",
}


class Konsole(Beobachter):
    def __init__(self, ketzer: bool) -> None:
        self._ketzer = ketzer

    def bei_aktion(self, schritt: int, aktion: Aktion) -> None:
        print(f"\n[{schritt}] {aktion.gedanke}")
        print(f"    → {aktion.werkzeug}: {_erste_zeile(aktion.eingabe)}")

    def bei_ergebnis(self, ergebnis: str) -> None:
        print(f"    ← {_erste_zeile(ergebnis)}")

    def bei_formatfehler(self, fehler: str) -> None:
        if self._ketzer:
            print(f"    ! Formatfehler: {fehler}")
        else:
            print(
                f"    ! Formatfehler: {fehler}\n    ! Das Orakel stammelt. Ich mahne zur Ordnung."
            )


def _erste_zeile(text: str, laenge: int = 90) -> str:
    zeile = text.strip().split("\n", 1)[0]
    return zeile if len(zeile) <= laenge else zeile[: laenge - 1] + "…"


def frage_nach(ketzer: bool) -> Bestaetigung:
    def bestaetigen(befehl: str, grund: str | None) -> bool:
        if not ketzer:
            print(f"\n{GEBET}")
        warnung = f"  ⚠ RISIKO: {grund}\n" if grund else ""
        antwort = input(f"{warnung}  Befehl ausführen? $ {befehl}\n  [j/N] ").strip().lower()
        return antwort in ("j", "ja", "y", "yes")

    return bestaetigen


def lies_argumente(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Servitor MC-01 – ein einfacher Coding-Agent")
    parser.add_argument(
        "aufgabe", nargs="?", help="Was der Servitor tun soll (ohne Angabe: Chat-Modus)"
    )
    parser.add_argument("--sichtbar", action="store_true", help="Browser mit Fenster starten")
    parser.add_argument("--ketzer", action="store_true", help="Persona abschalten")
    parser.add_argument(
        "--auto", action="store_true", help="Nur riskante Befehle bestätigen lassen"
    )
    parser.add_argument(
        "--config", type=Path, default=Path(__file__).parent / "config.toml", help="config.toml"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug-Logging")
    return parser.parse_args(argv)


def zeige_ergebnis(ergebnis: Ergebnis, ketzer: bool) -> None:
    print()
    if ketzer:
        print(f"Status: {ergebnis.status.value} nach {ergebnis.schritte} Schritt(en)")
    else:
        print(ABSCHLUSS[ergebnis.status])
    print(ergebnis.text)


def chat(agent: Agent, ketzer: bool, eingabe: Callable[[str], str] = input) -> int:
    """Nimmt Aufgaben im Dialog entgegen, bis der Nutzer /ende eingibt oder Strg+D drückt."""
    print(CHAT_HILFE if ketzer else f"{CHAT_GRUSS}\n{CHAT_HILFE}")
    while True:
        try:
            zeile = eingabe("\nDu> " if ketzer else "\nBittsteller> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not zeile:
            continue
        if zeile.lower() in ENDE_BEFEHLE:
            break
        if zeile.lower() == "/hilfe":
            print(CHAT_HILFE)
            continue
        if zeile.lower() == "/neu":
            agent.vergessen()
            print("Kontext gelöscht." if ketzer else CHAT_VERGESSEN)
            continue

        try:
            ergebnis = agent.ausfuehren(zeile)
        except KeyboardInterrupt:
            print("\nAbgebrochen." if ketzer else f"\n{CHAT_UNTERBROCHEN}")
            continue
        zeige_ergebnis(ergebnis, ketzer)
        if ergebnis.status is Status.BLOCKIERT:
            # Bei Bot-Erkennung nicht weiter anfragen (Spielregeln).
            return 1
    print("Beendet." if ketzer else CHAT_ABSCHIED)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = lies_argumente(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    config = lade_config(args.config)
    config.workspace.mkdir(parents=True, exist_ok=True)

    print(BANNER_NEUTRAL if args.ketzer else BANNER)
    if not args.ketzer:
        if args.aufgabe:
            print(f"Ich empfange die Aufgabe des Bittstellers: {args.aufgabe}")
        print(f"Heiliger Arbeitsbereich: {config.workspace}\n")

    werkzeuge = erzeuge_werkzeuge(
        config.workspace,
        frage_nach(args.ketzer),
        befehl_timeout=config.befehl_timeout,
        immer_fragen=not args.auto,
    )

    # Erst hier importieren, damit --help auch ohne Playwright funktioniert.
    from servitor.llm.browser import BrowserBackend

    try:
        with BrowserBackend(
            sichtbar=args.sichtbar,
            pause_sekunden=config.pause_sekunden,
            antwort_timeout=config.antwort_timeout,
            stabil_sekunden=config.stabil_sekunden,
            captcha_wartezeit=config.captcha_wartezeit,
            bei_captcha=lambda: print(CAPTCHA_BITTE_NEUTRAL if args.ketzer else CAPTCHA_BITTE),
        ) as backend:
            agent = Agent(
                backend, werkzeuge, config, ketzer=args.ketzer, beobachter=Konsole(args.ketzer)
            )
            if args.aufgabe is None:
                return chat(agent, args.ketzer)
            ergebnis = agent.ausfuehren(args.aufgabe)
    except KeyboardInterrupt:
        print("\nAbgebrochen." if args.ketzer else "\n++ Der Fleischling unterbricht die Riten. ++")
        return 130
    except BackendFehler as fehler:
        zeige_ergebnis(Ergebnis(Status.BACKEND_FEHLER, str(fehler), 0), args.ketzer)
        return 1

    zeige_ergebnis(ergebnis, args.ketzer)
    return 0 if ergebnis.status is Status.FERTIG else 1


if __name__ == "__main__":
    sys.exit(main())
