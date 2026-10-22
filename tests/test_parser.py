import pytest

from servitor.parser import Aktion, Fertig, FormatFehler, parse_antwort

EINFACH = """GEDANKE: Ich sichte die heiligen Dateien.
AKTION: dateien_listen
EINGABE:
.
ENDE"""


def test_einfache_aktion() -> None:
    assert parse_antwort(EINFACH) == Aktion(
        gedanke="Ich sichte die heiligen Dateien.", werkzeug="dateien_listen", eingabe="."
    )


def test_eingabe_im_codeblock_wie_vorgeschrieben() -> None:
    text = """GEDANKE: Ich schreibe die heilige Datei.
AKTION: datei_schreiben
EINGABE:
```
hallo.py

# Segen des Omnissiah auf diesem Code
print('Ave Omnissiah')  # *wichtig*
```
ENDE"""
    ergebnis = parse_antwort(text)
    assert isinstance(ergebnis, Aktion)
    assert ergebnis.eingabe == (
        "hallo.py\n\n# Segen des Omnissiah auf diesem Code\nprint('Ave Omnissiah')  # *wichtig*"
    )


def test_codeblock_mit_sprachangabe() -> None:
    text = "GEDANKE: x\nAKTION: befehl\nEINGABE:\n```bash\npython3 hallo.py\n```\nENDE"
    ergebnis = parse_antwort(text)
    assert isinstance(ergebnis, Aktion)
    assert ergebnis.eingabe == "python3 hallo.py"


def test_als_block_setzt_eingabe_in_codeblock() -> None:
    block = Aktion(gedanke="x", werkzeug="befehl", eingabe="# kommentar").als_block()
    assert "EINGABE:\n```\n# kommentar\n```\nENDE" in block


def test_mehrzeiliger_gedanke_und_eingabe() -> None:
    text = """GEDANKE: Erste Zeile
zweite Zeile
AKTION: datei_schreiben
EINGABE:
hallo.py

def main() -> None:
    print("hallo")
ENDE"""
    ergebnis = parse_antwort(text)
    assert isinstance(ergebnis, Aktion)
    assert ergebnis.gedanke == "Erste Zeile\nzweite Zeile"
    assert ergebnis.eingabe == 'hallo.py\n\ndef main() -> None:\n    print("hallo")'


def test_fertig() -> None:
    text = "FERTIG:\nDer Maschinengeist ist besänftigt.\nLob dem Omnissiah.\nENDE"
    assert parse_antwort(text) == Fertig(
        bericht="Der Maschinengeist ist besänftigt.\nLob dem Omnissiah."
    )


def test_fertig_mit_text_in_derselben_zeile() -> None:
    assert parse_antwort("FERTIG: Erledigt.\nENDE") == Fertig(bericht="Erledigt.")


def test_eingabe_in_derselben_zeile() -> None:
    text = "GEDANKE: x\nAKTION: befehl\nEINGABE: ls -la\nENDE"
    ergebnis = parse_antwort(text)
    assert isinstance(ergebnis, Aktion)
    assert ergebnis.eingabe == "ls -la"


def test_fehlendes_ende() -> None:
    with pytest.raises(FormatFehler, match="ENDE"):
        parse_antwort("GEDANKE: x\nAKTION: dateien_listen\nEINGABE:\n.")


def test_fehlendes_ende_bei_fertig() -> None:
    with pytest.raises(FormatFehler, match="ENDE"):
        parse_antwort("FERTIG:\nAlles erledigt.")


def test_zwei_aktionen() -> None:
    with pytest.raises(FormatFehler, match="Mehr als ein Block"):
        parse_antwort(EINFACH + "\n\n" + EINFACH)


def test_aktion_und_danach_fertig() -> None:
    with pytest.raises(FormatFehler, match="Mehr als ein Block"):
        parse_antwort(EINFACH + "\nFERTIG:\nfertig\nENDE")


def test_fehlende_aktion() -> None:
    with pytest.raises(FormatFehler, match="AKTION"):
        parse_antwort("GEDANKE: Ich denke nur nach.\nENDE")


def test_fehlende_eingabe() -> None:
    with pytest.raises(FormatFehler, match="EINGABE"):
        parse_antwort("GEDANKE: x\nAKTION: dateien_listen\nENDE")


def test_kein_block() -> None:
    with pytest.raises(FormatFehler, match="Kein Block"):
        parse_antwort("Hier ist eine hilfreiche Antwort ohne jedes Format.")


def test_markdown_codeblock_um_den_block() -> None:
    text = "Gerne, hier ist meine Antwort:\n\n```\n" + EINFACH + "\n```\n\nViel Erfolg!"
    assert parse_antwort(text) == parse_antwort(EINFACH)


def test_fettgedruckte_schluessel() -> None:
    text = "**GEDANKE:** Ich sichte.\n**AKTION:** `dateien_listen`\n**EINGABE:**\n.\n**ENDE**"
    assert parse_antwort(text) == Aktion(
        gedanke="Ich sichte.", werkzeug="dateien_listen", eingabe="."
    )


def test_codezaun_innerhalb_der_eingabe_wird_entfernt() -> None:
    text = """GEDANKE: Ich schreibe Code.
AKTION: datei_schreiben
EINGABE:
```python
skript.py

print("x")
```
ENDE"""
    ergebnis = parse_antwort(text)
    assert isinstance(ergebnis, Aktion)
    assert ergebnis.eingabe == 'skript.py\n\nprint("x")'


def test_quellenangaben_dazwischen() -> None:
    text = """GEDANKE: Laut Dokumentation listet man Dateien so.
docs.python.org +2
AKTION: dateien_listen
Quellen: stackoverflow.com
EINGABE:
.
ENDE
Quellen anzeigen · wikipedia.org"""
    ergebnis = parse_antwort(text)
    assert isinstance(ergebnis, Aktion)
    assert ergebnis.werkzeug == "dateien_listen"
    assert ergebnis.eingabe == "."
    assert "docs.python.org" in ergebnis.gedanke


def test_unsichtbare_zeichen_und_windows_zeilenenden() -> None:
    text = "﻿GEDANKE: x\r\nAKTION: dateien_listen\r\nEINGABE:\r\n.\r\nENDE\r\n"
    ergebnis = parse_antwort(text)
    assert isinstance(ergebnis, Aktion)
    assert ergebnis.eingabe == "."


def test_werkzeugname_wird_normalisiert() -> None:
    ergebnis = parse_antwort("GEDANKE: x\nAKTION: Datei_Lesen\nEINGABE:\na.txt\nENDE")
    assert isinstance(ergebnis, Aktion)
    assert ergebnis.werkzeug == "datei_lesen"


def test_als_block_ist_wieder_parsebar() -> None:
    aktion = parse_antwort(EINFACH)
    assert parse_antwort(aktion.als_block()) == aktion
