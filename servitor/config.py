"""Laden der Einstellungen aus config.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MIN_PAUSE_SEKUNDEN = 5.0


@dataclass(frozen=True)
class Config:
    max_schritte: int = 25
    max_fehler_in_folge: int = 3
    max_prompt_zeichen: int = 8000
    pause_sekunden: float = MIN_PAUSE_SEKUNDEN
    antwort_timeout: float = 90.0
    stabil_sekunden: float = 2.0
    captcha_wartezeit: float = 300.0
    workspace: Path = Path("workspace")
    befehl_timeout: float = 60.0


def lade_config(pfad: Path) -> Config:
    """Liest die Konfiguration; fehlt die Datei, gelten die Standardwerte."""
    if not pfad.exists():
        return Config(workspace=pfad.parent / "workspace")
    with pfad.open("rb") as datei:
        daten = tomllib.load(datei)
    return _baue_config(daten, pfad.parent)


def _baue_config(daten: dict[str, Any], basis: Path) -> Config:
    standard = Config()
    agent = daten.get("agent", {})
    browser = daten.get("browser", {})
    werkzeuge = daten.get("werkzeuge", {})

    workspace = Path(werkzeuge.get("workspace", standard.workspace))
    if not workspace.is_absolute():
        workspace = basis / workspace

    return Config(
        max_schritte=max(1, int(agent.get("max_schritte", standard.max_schritte))),
        max_fehler_in_folge=max(
            1, int(agent.get("max_fehler_in_folge", standard.max_fehler_in_folge))
        ),
        max_prompt_zeichen=int(agent.get("max_prompt_zeichen", standard.max_prompt_zeichen)),
        pause_sekunden=max(
            MIN_PAUSE_SEKUNDEN, float(browser.get("pause_sekunden", standard.pause_sekunden))
        ),
        antwort_timeout=float(browser.get("antwort_timeout", standard.antwort_timeout)),
        stabil_sekunden=float(browser.get("stabil_sekunden", standard.stabil_sekunden)),
        captcha_wartezeit=float(browser.get("captcha_wartezeit", standard.captcha_wartezeit)),
        workspace=workspace,
        befehl_timeout=float(werkzeuge.get("befehl_timeout", standard.befehl_timeout)),
    )
