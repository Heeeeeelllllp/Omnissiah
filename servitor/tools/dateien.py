"""Dateiwerkzeuge: lesen, schreiben, auflisten – nur innerhalb des Workspace."""

from __future__ import annotations

from pathlib import Path

from servitor.tools.basis import PfadFehler, sicherer_pfad

MAX_LESEZEICHEN = 20_000


def datei_lesen(eingabe: str, workspace: Path) -> str:
    try:
        pfad = sicherer_pfad(workspace, eingabe)
    except PfadFehler as fehler:
        return f"FEHLER: {fehler}"
    if not pfad.is_file():
        return f"FEHLER: Datei nicht gefunden: {eingabe.strip()}"
    inhalt = pfad.read_text(encoding="utf-8", errors="replace")
    if len(inhalt) > MAX_LESEZEICHEN:
        rest = len(inhalt) - MAX_LESEZEICHEN
        return inhalt[:MAX_LESEZEICHEN] + f"\n[... {rest} weitere Zeichen abgeschnitten]"
    return inhalt


def datei_schreiben(eingabe: str, workspace: Path) -> str:
    """Eingabe: erste Zeile Pfad, dann eine Leerzeile, dann der Inhalt."""
    pfad_text, _, inhalt = eingabe.partition("\n")
    if not pfad_text.strip():
        return "FEHLER: In der ersten Zeile der Eingabe fehlt der Dateipfad."
    try:
        pfad = sicherer_pfad(workspace, pfad_text)
    except PfadFehler as fehler:
        return f"FEHLER: {fehler}"
    if pfad.is_dir():
        return f"FEHLER: {pfad_text.strip()} ist ein Verzeichnis."
    inhalt = inhalt.removeprefix("\n")
    if inhalt and not inhalt.endswith("\n"):
        inhalt += "\n"
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(inhalt, encoding="utf-8")
    return f"OK: {len(inhalt)} Zeichen nach {pfad_text.strip()} geschrieben."


def dateien_listen(eingabe: str, workspace: Path) -> str:
    try:
        pfad = sicherer_pfad(workspace, eingabe)
    except PfadFehler as fehler:
        return f"FEHLER: {fehler}"
    if not pfad.is_dir():
        return f"FEHLER: Verzeichnis nicht gefunden: {eingabe.strip() or '.'}"
    eintraege = sorted(pfad.iterdir(), key=lambda p: (not p.is_dir(), p.name))
    if not eintraege:
        return "(leer)"
    return "\n".join(p.name + "/" if p.is_dir() else p.name for p in eintraege)
