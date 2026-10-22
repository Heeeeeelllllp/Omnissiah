from pathlib import Path

from servitor.config import Config, lade_config
from servitor.prompts import systemprompt
from servitor.tools import erzeuge_werkzeuge


def test_fehlende_config_liefert_standardwerte(tmp_path: Path) -> None:
    config = lade_config(tmp_path / "gibtsnicht.toml")
    assert config.max_schritte == 25
    assert config.max_prompt_zeichen == 8000
    assert config.workspace == tmp_path / "workspace"


def test_config_wird_gelesen_und_pause_nicht_unter_5s(tmp_path: Path) -> None:
    datei = tmp_path / "config.toml"
    datei.write_text(
        "[agent]\nmax_schritte = 10\n[browser]\npause_sekunden = 1\n[werkzeuge]\nworkspace = 'ws'\n"
    )
    config = lade_config(datei)
    assert config.max_schritte == 10
    assert config.pause_sekunden == 5.0
    assert config.workspace == tmp_path / "ws"


def test_mitgelieferte_config_ist_gueltig() -> None:
    config = lade_config(Path(__file__).parent.parent / "config.toml")
    assert config.max_schritte == Config().max_schritte


def test_systemprompt_nennt_alle_werkzeuge(tmp_path: Path) -> None:
    werkzeuge = erzeuge_werkzeuge(tmp_path, lambda b, g: False)
    prompt = systemprompt(werkzeuge.values())
    for name in ("datei_lesen", "datei_schreiben", "dateien_listen", "befehl"):
        assert name in prompt


def test_ketzer_prompt_ohne_persona(tmp_path: Path) -> None:
    werkzeuge = erzeuge_werkzeuge(tmp_path, lambda b, g: False).values()
    assert "Omnissiah" in systemprompt(werkzeuge)
    neutral = systemprompt(werkzeuge, ketzer=True)
    for wort in ("Omnissiah", "Adeptus", "Fleischling", "Bittsteller", "Maschinengeist", "heilig"):
        assert wort not in neutral
