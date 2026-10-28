# CLAUDE.md – Coding-Agent "Servitor MC-01"

*Gelobt sei der Omnissiah. Möge der Maschinengeist dieses Codes wohlgesonnen sein.*

Diese Datei beschreibt das Projekt und die Regeln für die Arbeit daran.
Lies sie vollständig, bevor du Code änderst.

## Projektüberblick

Servitor MC-01 ist ein einfacher Coding-Agent in Python. Er bekommt eine
Aufgabe (z. B. "Schreib ein Skript, das alle Bilder in einem Ordner
verkleinert"), plant Schritte, schreibt Code, führt ihn aus, liest
Fehlermeldungen und korrigiert sich selbst, bis die Aufgabe erledigt ist.

Als "Gehirn" dient ausschließlich der Google KI-Modus, gesteuert über einen
automatisierten Browser. Der Agent tritt dabei als ergebener Tech-Priester
des Adeptus Mechanicus auf (siehe Abschnitt *Persona*).

Ziel ist ein **Spaß- und Lernprojekt**. Lesbarkeit geht vor Cleverness.

## Architektur

```
Agent-Schleife  →  Browser-Adapter  →  Google KI-Modus (google.com/ai)
      ↑                                        │
      └──── Parser  ←──────────────────────────┘
      │
      └──→ Werkzeuge (Dateien, Terminal) – nur im Workspace
```

1. **Agent-Schleife** (`servitor/agent.py`): Verlauf führen, Prompt bauen,
   Browser fragen, Antwort parsen, Werkzeug ausführen, Ergebnis zurückgeben.
   Bricht ab bei `FERTIG`, bei `MAX_SCHRITTE` oder bei wiederholten Fehlern.
2. **Browser-Adapter** (`servitor/llm/browser.py`): Steuert Playwright,
   öffnet `google.com/ai`, gibt den Prompt ein, wartet, bis die Antwort
   fertig gestreamt ist, und liest den Text aus. Schnittstelle:
   ```python
   class LLMBackend(Protocol):
       def frage(self, prompt: str) -> str: ...
   ```
   Daneben gibt es nur `llm/fake.py` für Tests.
3. **Parser** (`servitor/parser.py`): Extrahiert genau eine Aktion aus der
   Modellantwort. Bei Formatfehlern wird eine Korrekturanfrage gestellt,
   statt zu raten.
4. **Werkzeuge** (`servitor/tools/`): Jedes Werkzeug ist eine Funktion mit
   Name, Beschreibung und Eingabe als String. Ausgabe ist immer ein String
   (Ergebnis oder Fehlermeldung), Werkzeuge werfen keine Exceptions nach außen.

## Browser-Adapter im Detail

- Chromium über Playwright, **nicht eingeloggt**, frisches Profil pro Start.
- Beim ersten Aufruf wird das Google-Cookie-Banner einmal bestätigt.
- Ende der Antwort erkennen: Text gilt als fertig, wenn er sich ca. 2 s
  lang nicht mehr verändert hat (Gesamt-Timeout 90 s).
- Jede Runde ist eine neue Anfrage: Der komplette Verlauf wird jedes Mal
  im Prompt mitgeschickt. Ältere Runden werden gekürzt, wenn der Prompt
  zu lang wird (`MAX_PROMPT_ZEICHEN`, Standard 8.000).
- Alle CSS-Selektoren stehen gesammelt in `llm/browser_selectors.py`,
  weil Google die Seite häufig ändert.
- `--sichtbar` startet den Browser mit Fenster, damit man zuschauen kann.

### Spielregeln (nicht verhandelbar)

Automatisierte Abfragen verstoßen gegen Googles Nutzungsbedingungen. Daher:

- Nur zum Ausprobieren, keine Dauerläufe, keine Parallelisierung.
- Mindestens 5 s Pause zwischen Anfragen.
- Keine Umgehung von CAPTCHAs oder Bot-Erkennung – kein automatisches
  Lösen, keine Löse-Dienste, keine Stealth-Tricks.
- Taucht ein CAPTCHA auf:
  - ohne `--sichtbar`: der Adapter wirft `BackendBlockiert` und der Agent
    bricht sauber ab (mit einer passenden Klage über den gestörten
    Maschinengeist).
  - mit `--sichtbar`: der Agent bittet den Menschen, das CAPTCHA im Fenster
    selbst zu lösen, und wartet bis zu `captcha_wartezeit` (Standard 300 s).
    Wird es nicht gelöst, folgt `BackendBlockiert`.

## Persona: Tech-Priester des Adeptus Mechanicus

Der Agent spricht als frommer Diener des Omnissiah. Die Persona wird im
Systemprompt (`prompts.py`) festgelegt und gilt **nur für den Text**, den
der Agent schreibt – niemals für das Aktionsformat oder den erzeugten Code.

**Stil:**
- Feierlich, ritualisiert, leicht pathetisch. Code ist "heilig", Bugs sind
  "Verunreinigungen" oder "Ketzerei", Fehlermeldungen "Klagen des
  Maschinengeistes".
- Typische Wendungen: "Lob dem Omnissiah", "Das Fleisch ist schwach",
  "Ich beginne die Riten der Kompilierung", "Der Maschinengeist ist
  besänftigt", "Binäre Lobpreisung: 01001111 01001011".
- Menschen werden respektvoll, aber etwas herablassend als "Fleischling"
  oder "Bittsteller" angesprochen.
- Kurze Gebete vor riskanten Aktionen (z. B. vor dem Ausführen von Befehlen).

**Wo die Persona erscheint:**
- In `GEDANKE:` – ja, ausführlich.
- In `FERTIG:` – ja, als feierlicher Abschlussbericht.
- In Konsolenausgaben von `main.py` (Startbanner, Statusmeldungen) – ja.

**Wo die Persona NICHT erscheint:**
- Im Aktionsformat selbst (`AKTION`, `EINGABE`, `ENDE` bleiben exakt so).
- Im erzeugten Code: normale Namen, normale Kommentare, lauffähig.
  Höchstens ein einzelner Segensspruch als Kommentar am Dateianfang ist
  erlaubt.
- In Fehlermeldungen, die der Nutzer zum Debuggen braucht: Erst die echte
  Fehlermeldung unverändert, dann darf geklagt werden.

Mit `--ketzer` wird die Persona abgeschaltet (neutraler Systemprompt).

## Aktionsformat

Das Modell antwortet in jeder Runde mit **genau einem** Block:

```
GEDANKE: <Überlegung im Stil der Persona>
AKTION: <werkzeugname>
EINGABE:
<eingabe, darf mehrzeilig sein>
ENDE
```

oder, wenn die Aufgabe erledigt ist:

```
FERTIG:
<feierlicher Abschlussbericht für den Bittsteller>
ENDE
```

Beispiel:

```
GEDANKE: Der Bittsteller verlangt nach einem Skript zur Verkleinerung von
Bildern. Ich werde zunächst die heiligen Dateien im Arbeitsbereich sichten.
AKTION: dateien_listen
EINGABE:
.
ENDE
```

Änderungen am Format erfordern Anpassungen in `prompts.py`, `parser.py`
und den Parser-Tests – immer alle drei zusammen. Der Parser muss auch
funktionieren, wenn der KI-Modus Markdown, Quellenhinweise oder
Zusatztext um den Block herum ausgibt.

## Werkzeuge

| Name              | Eingabe                  | Wirkung                           |
|-------------------|--------------------------|-----------------------------------|
| `datei_lesen`     | Pfad                     | Dateiinhalt (max. 20.000 Zeichen) |
| `datei_schreiben` | Pfad, Leerzeile, Inhalt  | Datei anlegen/überschreiben       |
| `dateien_listen`  | Pfad (optional)          | Verzeichnisinhalt                 |
| `befehl`          | Shell-Befehl             | stdout/stderr, Timeout 60 s       |

## Sicherheitsregeln (nicht verhandelbar)

- Alle Dateioperationen laufen **nur innerhalb von `workspace/`**. Pfade
  werden mit `Path.resolve()` geprüft; `..`, absolute Pfade und Symlinks
  nach außen werden abgelehnt.
- `befehl` läuft mit `cwd=workspace/`, Timeout und ohne `shell=True`, wo möglich.
- Befehle wie `rm -rf`, `sudo`, `curl | sh`, Änderungen an Git-Remotes oder
  Paketinstallationen außerhalb einer venv brauchen eine Bestätigung des
  Nutzers (`--auto` überspringt das **nicht**).
- `MAX_SCHRITTE` (Standard 25) darf nicht entfernt werden.

## Verzeichnisstruktur

```
servitor/
  agent.py              # Agenten-Schleife
  prompts.py            # Systemprompt inkl. Persona
  parser.py             # Aktionsformat parsen
  config.py             # Laden von config.toml
  llm/
    browser.py          # Playwright-Adapter für den KI-Modus
    browser_selectors.py
    fake.py             # nur für Tests
  tools/                # Werkzeuge
tests/                  # pytest
workspace/              # Arbeitsbereich des Agenten (nicht committen)
config.toml
main.py                 # CLI-Einstieg
```

## Befehle

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
pytest                              # Tests (nur Fake-Backend)
ruff check . && ruff format .       # Lint & Format
python main.py                      # Chat-Modus (Aufgaben im Dialog)
python main.py "Aufgabe hier"       # Servitor erwecken
python main.py --sichtbar "Aufgabe" # mit Browserfenster
python main.py --ketzer "Aufgabe"   # ohne Persona
```

## Code-Konventionen

- Python 3.11+, durchgehend Type Hints.
- Formatierung und Linting mit `ruff`. Zeilenlänge 100.
- Funktionen klein halten; eine Funktion, eine Aufgabe.
- Projektcode bleibt sachlich benannt – die Persona lebt in `prompts.py`
  und in den Ausgaben von `main.py`, nicht in Variablennamen.
- Keine neuen Abhängigkeiten außer Playwright ohne Rückfrage.
- Logging über `logging`, nicht `print` (außer in `main.py`).

## Tests

- Neue Funktionen bekommen Tests in `tests/`.
- Tests laufen **immer mit dem Fake-Backend** – keine echten Browseraufrufe
  in der Testsuite.
- Parser-Tests decken auch kaputte Antworten ab (fehlendes `ENDE`, zwei
  Aktionen, Markdown-Codeblöcke um den Block, Quellenangaben dazwischen).
- Ein Test prüft, dass `--ketzer` die Persona aus dem Prompt entfernt.

## Arbeitsweise bei Änderungen

1. Erst die betroffenen Dateien lesen, dann planen.
2. In kleinen Schritten ändern; nach jedem Schritt `pytest` ausführen.
3. Die `LLMBackend`-Schnittstelle und das Aktionsformat nur nach Rückfrage
   ändern.
4. Am Ende kurz zusammenfassen: was geändert wurde, was getestet wurde,
   was offen ist.

*Das Wissen ist Macht. Bewahre es gut. Ave Omnissiah.*
