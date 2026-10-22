"""Werkzeug `befehl`: führt einen Shell-Befehl im Workspace aus."""

from __future__ import annotations

import re
import shlex
import subprocess
from collections.abc import Callable
from pathlib import Path

MAX_AUSGABEZEICHEN = 10_000

# Bekommt Befehl und Grund (None = kein besonderes Risiko), gibt True zurück, wenn erlaubt.
Bestaetigung = Callable[[str, str | None], bool]

_GEFAEHRLICH: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\brm\b[^|;&\n]*\s(-[a-zA-Z]*[rR]|--recursive)"), "rekursives Löschen (rm -r)"),
    (re.compile(r"\bsudo\b"), "Root-Rechte (sudo)"),
    (
        re.compile(r"\b(curl|wget)\b[^\n]*\|\s*(sudo\s+)?(ba|z|da)?sh\b"),
        "Skript aus dem Netz ausführen (curl | sh)",
    ),
    (
        re.compile(r"\bgit\s+(remote\s+(add|set-url|remove|rm|rename)|push)\b"),
        "Änderung an Git-Remotes",
    ),
    (re.compile(r"\bapt(-get)?\s+install\b"), "Systempaket installieren"),
    (re.compile(r"\bnpm\s+(install|i)\b[^\n]*\s(-g|--global)\b"), "globales npm-Paket"),
    (re.compile(r"\bconda\s+install\b"), "conda-Paket installieren"),
]
_PIP_INSTALL = re.compile(r"\bpip3?\s+install\b")
_WORKSPACE_VENV = re.compile(r"(^|[\s/])\.?venv/bin/|\bactivate\b")
_SHELL_ZEICHEN = re.compile(r"[|&;<>()$`*?~\n]")


def gefahr_grund(befehl: str) -> str | None:
    """Gibt zurück, warum ein Befehl bestätigt werden muss – oder None."""
    for muster, grund in _GEFAEHRLICH:
        if muster.search(befehl):
            return grund
    if _PIP_INSTALL.search(befehl) and not _WORKSPACE_VENV.search(befehl):
        return "Paketinstallation außerhalb einer venv"
    return None


def befehl_ausfuehren(
    eingabe: str,
    workspace: Path,
    timeout: float,
    bestaetigen: Bestaetigung,
    immer_fragen: bool,
) -> str:
    befehl = eingabe.strip()
    if not befehl:
        return "FEHLER: Leerer Befehl."
    grund = gefahr_grund(befehl)
    if (grund is not None or immer_fragen) and not bestaetigen(befehl, grund):
        return "ABGELEHNT: Der Nutzer hat die Ausführung dieses Befehls nicht erlaubt."
    try:
        lauf = subprocess.run(
            _zerlege(befehl),
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return f"FEHLER: Zeitüberschreitung nach {timeout:g} s."
    except FileNotFoundError as fehler:
        return f"FEHLER: Programm nicht gefunden: {fehler.filename}"
    return _formatiere(lauf.returncode, lauf.stdout, lauf.stderr)


def _zerlege(befehl: str) -> list[str]:
    """Ohne Shell, wo möglich; Pipes, Umleitungen usw. brauchen /bin/sh."""
    if _SHELL_ZEICHEN.search(befehl):
        return ["/bin/sh", "-c", befehl]
    return shlex.split(befehl)


def _formatiere(code: int, stdout: str, stderr: str) -> str:
    text = f"Exit-Code: {code}\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"
    if len(text) > MAX_AUSGABEZEICHEN:
        rest = len(text) - MAX_AUSGABEZEICHEN
        return text[:MAX_AUSGABEZEICHEN] + f"\n[... {rest} weitere Zeichen abgeschnitten]"
    return text
