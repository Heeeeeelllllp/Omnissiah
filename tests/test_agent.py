from pathlib import Path

import pytest

from servitor.agent import Agent, Status, kuerze_verlauf
from servitor.config import Config
from servitor.llm import BackendBlockiert, BackendFehler
from servitor.llm.fake import FakeBackend
from servitor.tools import Werkzeug, erzeuge_werkzeuge


def immer_ja(befehl: str, grund: str | None) -> bool:
    return True


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


@pytest.fixture
def werkzeuge(workspace: Path) -> dict[str, Werkzeug]:
    return erzeuge_werkzeuge(workspace, immer_ja, befehl_timeout=5, immer_fragen=False)


def aktion(werkzeug: str, eingabe: str) -> str:
    return f"GEDANKE: Lob dem Omnissiah.\nAKTION: {werkzeug}\nEINGABE:\n{eingabe}\nENDE"


FERTIG = "FERTIG:\nDer Maschinengeist ist besänftigt.\nENDE"


def test_schreibt_datei_fuehrt_aus_und_wird_fertig(
    werkzeuge: dict[str, Werkzeug], workspace: Path
) -> None:
    backend = FakeBackend(
        [
            aktion("datei_schreiben", "hallo.py\n\nprint('Ave Omnissiah')"),
            aktion("befehl", "python3 hallo.py"),
            FERTIG,
        ]
    )
    ergebnis = Agent(backend, werkzeuge, Config()).ausfuehren("Schreib ein Hallo-Skript")

    assert ergebnis.status is Status.FERTIG
    assert ergebnis.text == "Der Maschinengeist ist besänftigt."
    assert ergebnis.schritte == 3
    assert (workspace / "hallo.py").exists()
    # Das Ergebnis des Befehls landet im nächsten Prompt
    assert "Ave Omnissiah" in backend.prompts[2]
    assert "Schreib ein Hallo-Skript" in backend.prompts[0]


def test_bricht_bei_max_schritte_ab(werkzeuge: dict[str, Werkzeug]) -> None:
    backend = FakeBackend([aktion("dateien_listen", ".")] * 10)
    ergebnis = Agent(backend, werkzeuge, Config(max_schritte=4)).ausfuehren("x")
    assert ergebnis.status is Status.MAX_SCHRITTE
    assert len(backend.prompts) == 4


def test_formatfehler_fuehrt_zu_korrekturanfrage(werkzeuge: dict[str, Werkzeug]) -> None:
    backend = FakeBackend(["Ich habe keine Lust auf Formate.", FERTIG])
    ergebnis = Agent(backend, werkzeuge, Config()).ausfuehren("x")
    assert ergebnis.status is Status.FERTIG
    assert "FORMATFEHLER" in backend.prompts[1]


def test_bricht_nach_wiederholten_formatfehlern_ab(werkzeuge: dict[str, Werkzeug]) -> None:
    backend = FakeBackend(["kaputt"] * 10)
    ergebnis = Agent(backend, werkzeuge, Config(max_fehler_in_folge=3)).ausfuehren("x")
    assert ergebnis.status is Status.ZU_VIELE_FEHLER
    assert len(backend.prompts) == 3


def test_unbekanntes_werkzeug_zaehlt_als_fehler(werkzeuge: dict[str, Werkzeug]) -> None:
    backend = FakeBackend([aktion("zaubern", "x")] * 5)
    ergebnis = Agent(backend, werkzeuge, Config(max_fehler_in_folge=2)).ausfuehren("x")
    assert ergebnis.status is Status.ZU_VIELE_FEHLER
    assert "Unbekanntes Werkzeug 'zaubern'" in backend.prompts[1]


def test_erfolgreiche_aktion_setzt_fehlerzaehler_zurueck(werkzeuge: dict[str, Werkzeug]) -> None:
    backend = FakeBackend(["kaputt", aktion("dateien_listen", "."), "kaputt", FERTIG])
    ergebnis = Agent(backend, werkzeuge, Config(max_fehler_in_folge=2)).ausfuehren("x")
    assert ergebnis.status is Status.FERTIG


def test_captcha_bricht_sauber_ab(werkzeuge: dict[str, Werkzeug]) -> None:
    backend = FakeBackend([BackendBlockiert("CAPTCHA")])
    ergebnis = Agent(backend, werkzeuge, Config()).ausfuehren("x")
    assert ergebnis.status is Status.BLOCKIERT


def test_backend_fehler_bricht_ab(werkzeuge: dict[str, Werkzeug]) -> None:
    backend = FakeBackend([BackendFehler("Timeout")])
    ergebnis = Agent(backend, werkzeuge, Config()).ausfuehren("x")
    assert ergebnis.status is Status.BACKEND_FEHLER


def test_prompt_bleibt_unter_dem_limit(werkzeuge: dict[str, Werkzeug], workspace: Path) -> None:
    (workspace / "gross.txt").write_text("x" * 15_000)
    backend = FakeBackend([aktion("datei_lesen", "gross.txt")] * 5 + [FERTIG])
    Agent(backend, werkzeuge, Config(max_prompt_zeichen=8000)).ausfuehren("x")
    assert all(len(p) <= 8000 for p in backend.prompts)
    assert "--- Runde 5 ---" in backend.prompts[-1]


def test_ketzer_entfernt_persona(werkzeuge: dict[str, Werkzeug]) -> None:
    fromm = FakeBackend([FERTIG])
    ketzer = FakeBackend([FERTIG])
    Agent(fromm, werkzeuge, Config()).ausfuehren("x")
    Agent(ketzer, werkzeuge, Config(), ketzer=True).ausfuehren("x")
    assert "Omnissiah" in fromm.prompts[0]
    for wort in ("Omnissiah", "Tech-Priester", "Fleischling", "Bittsteller", "Maschinengeist"):
        assert wort not in ketzer.prompts[0]
    assert "AKTION:" in ketzer.prompts[0]


def test_kuerze_verlauf_laesst_kurze_runden_in_ruhe() -> None:
    assert kuerze_verlauf(["a", "b"], 100) == ["a", "b"]


def test_kuerze_verlauf_kuerzt_zuerst_alte_runden() -> None:
    runden = ["a" * 1000, "b" * 1000, "c" * 100]
    gekuerzt = kuerze_verlauf(runden, 1000)
    assert gekuerzt[-1] == "c" * 100
    assert len("\n\n".join(gekuerzt)) <= 1000


def test_kuerze_verlauf_entfernt_notfalls_alte_runden() -> None:
    runden = ["a" * 500] * 10 + ["neu"]
    gekuerzt = kuerze_verlauf(runden, 400)
    assert gekuerzt[-1] == "neu"
    assert "entfernt" in gekuerzt[0]
    assert len("\n\n".join(gekuerzt)) <= 400


def test_kuerze_verlauf_kuerzt_notfalls_die_letzte_runde() -> None:
    gekuerzt = kuerze_verlauf(["x" * 5000], 200)
    assert len("\n\n".join(gekuerzt)) <= 200


def test_fruehere_aufgaben_stehen_im_naechsten_prompt(werkzeuge: dict[str, Werkzeug]) -> None:
    backend = FakeBackend([FERTIG, FERTIG])
    agent = Agent(backend, werkzeuge, Config())
    agent.ausfuehren("Schreib ein Hallo-Skript")
    agent.ausfuehren("Mach es lauter")

    assert "FRÜHERE AUFGABEN" not in backend.prompts[0]
    assert "Schreib ein Hallo-Skript" in backend.prompts[1]
    assert "Der Maschinengeist ist besänftigt." in backend.prompts[1]
    assert "Mach es lauter" in backend.prompts[1]


def test_vergessen_loescht_fruehere_aufgaben(werkzeuge: dict[str, Werkzeug]) -> None:
    backend = FakeBackend([FERTIG, FERTIG])
    agent = Agent(backend, werkzeuge, Config())
    agent.ausfuehren("Alte Aufgabe")
    agent.vergessen()
    agent.ausfuehren("Neue Aufgabe")
    assert "Alte Aufgabe" not in backend.prompts[1]


def test_prompt_mit_frueheren_aufgaben_bleibt_unter_dem_limit(
    werkzeuge: dict[str, Werkzeug],
) -> None:
    backend = FakeBackend([FERTIG] * 10)
    agent = Agent(backend, werkzeuge, Config(max_prompt_zeichen=8000))
    for _ in range(10):
        agent.ausfuehren("x" * 2000)
    assert all(len(p) <= 8000 for p in backend.prompts)
