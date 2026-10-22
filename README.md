# ⚙ Servitor MC-01

*Gelobt sei der Omnissiah. Möge der Maschinengeist dieses Codes wohlgesonnen sein.*

Servitor MC-01 ist ein kleiner Coding-Agent in Python. Er bekommt eine Aufgabe,
plant Schritte, schreibt Code, führt ihn aus, liest Fehlermeldungen und
korrigiert sich selbst, bis die Aufgabe erledigt ist.

Als „Gehirn“ dient der **Google KI-Modus**, gesteuert über einen automatisierten
Browser (Playwright). Dabei spricht der Agent als ergebener Tech-Priester des
Adeptus Mechanicus. Den erzeugten Code betrifft das nicht.

> **Spaß- und Lernprojekt.** Automatisierte Abfragen verstoßen gegen Googles
> Nutzungsbedingungen. Bitte nur zum Ausprobieren verwenden: keine Dauerläufe,
> keine Parallelisierung. Der Agent wartet mindestens 5 s zwischen Anfragen
> und umgeht CAPTCHAs nie. Ohne Fenster bricht er ab, mit `--sichtbar` bittet
> er dich, das CAPTCHA selbst zu lösen, und wartet so lange.

## Installation

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
```

Voraussetzung: Python 3.11 oder neuer. Auf Debian/Ubuntu fehlt das venv-Modul
oft, dann vorher `sudo apt install python3-venv` ausführen. Nach dem Aktivieren
der venv heißt der Befehl einfach `python`.

## Benutzung

Immer aus der aktivierten venv starten (`source .venv/bin/activate`). Ein anderes
Python, etwa aus conda, bringt eine andere Playwright-Version mit und findet den
installierten Browser nicht.

```bash
python main.py "Schreib ein Skript, das alle Bilder in einem Ordner verkleinert"
python main.py --sichtbar "Aufgabe"   # Browserfenster anzeigen und zuschauen
python main.py --ketzer "Aufgabe"     # ohne Persona, neutraler Ton
python main.py --auto "Aufgabe"       # nur riskante Befehle bestätigen
```

| Option          | Wirkung                                                         |
|-----------------|-----------------------------------------------------------------|
| `--sichtbar`    | Chromium mit Fenster starten                                    |
| `--ketzer`      | Persona abschalten (neutraler Systemprompt und neutrale Ausgabe) |
| `--auto`        | Normale Befehle ohne Rückfrage ausführen (riskante weiterhin nur mit Bestätigung) |
| `--config PFAD` | Andere `config.toml` verwenden                                  |
| `-v`            | Debug-Logging                                                   |

Alle Dateien, die der Agent anlegt, landen in `workspace/`.

### Beispielausgabe

```
      ⚙  SERVITOR MC-01  ⚙
  ++ Lob dem Omnissiah. Der Maschinengeist erwacht. ++

[1] Der Bittsteller verlangt nach einem Skript. Ich sichte zunächst die heiligen Dateien.
    → dateien_listen: .
    ← (leer)
...
++ Das Werk ist vollbracht. Der Maschinengeist ist besänftigt. ++
```

## So funktioniert es

```
Agent-Schleife  →  Browser-Adapter  →  Google KI-Modus (google.com/ai)
      ↑                                        │
      └──── Parser  ←──────────────────────────┘
      │
      └──→ Werkzeuge (Dateien, Terminal) – nur im Workspace
```

1. Die **Agent-Schleife** baut aus Systemprompt, Aufgabe und bisherigem Verlauf
   einen Prompt. Ist er zu lang, werden ältere Runden gekürzt.
2. Der **Browser-Adapter** stellt ihn als neue Anfrage im KI-Modus. Die Antwort
   gilt als fertig, wenn sie sich etwa 2 s nicht mehr ändert.
3. Der **Parser** liest genau einen Block aus der Antwort:

   ````
   GEDANKE: <Überlegung>
   AKTION: <werkzeugname>
   EINGABE:
   ```
   <eingabe>
   ```
   ENDE
   ````

   oder `FERTIG: … ENDE`. Die Eingabe steht in einem Codeblock, weil der KI-Modus
   Markdown darstellt und sonst Zeichen wie `#` (Python-Kommentare) verschwinden. Ist die Antwort kaputt, schickt der Agent eine
   Korrekturanfrage und rät nicht.
4. Das **Werkzeug** wird ausgeführt, und das Ergebnis geht in die nächste Runde.

Der Agent bricht ab bei `FERTIG`, nach `max_schritte` (Standard 25), nach
mehreren unbrauchbaren Antworten in Folge oder wenn Google blockiert.

### Werkzeuge

| Name              | Eingabe                  | Wirkung                           |
|-------------------|--------------------------|-----------------------------------|
| `datei_lesen`     | Pfad                     | Dateiinhalt (max. 20.000 Zeichen) |
| `datei_schreiben` | Pfad, Leerzeile, Inhalt  | Datei anlegen oder überschreiben  |
| `dateien_listen`  | Pfad (optional)          | Verzeichnisinhalt                 |
| `befehl`          | Shell-Befehl             | Exit-Code, stdout, stderr (Timeout 60 s) |

## Sicherheit

- Dateioperationen sind auf `workspace/` beschränkt. `..`, absolute Pfade und
  Symlinks nach außen werden abgelehnt.
- Befehle laufen mit `cwd=workspace/` und Timeout.
- Ohne `--auto` muss jeder Befehl bestätigt werden.
- Auch mit `--auto` brauchen diese Befehle immer eine Bestätigung: `rm -r`,
  `sudo`, `curl | sh`, Änderungen an Git-Remotes und `git push`, `pip install`
  außerhalb einer Workspace-venv, `apt install`, `conda install` und `npm install -g`.

Der Agent führt echten Code auf deinem Rechner aus. Lies die Befehle, bevor du sie bestätigst.

## Konfiguration

Die Einstellungen stehen in `config.toml`:

```toml
[agent]
max_schritte = 25
max_fehler_in_folge = 3
max_prompt_zeichen = 8000

[browser]
pause_sekunden = 5      # Werte unter 5 werden auf 5 angehoben
antwort_timeout = 90
stabil_sekunden = 2
captcha_wartezeit = 300 # nur mit --sichtbar: Zeit für dich, ein CAPTCHA zu lösen

[werkzeuge]
workspace = "workspace"
befehl_timeout = 60
```

## Wenn der Browser nichts mehr findet

Google ändert die Seite häufig. Alle CSS-Selektoren stehen deshalb gesammelt in
`servitor/llm/browser_selectors.py`. Starte den Agenten mit `--sichtbar`,
untersuche die Seite mit den DevTools und passe dort das Eingabefeld, den
Antwort-Container und den Cookie-Button an.

## Entwicklung

```bash
pytest                           # Tests (nur Fake-Backend, kein echter Browser)
ruff check . && ruff format .    # Lint und Format
```

Projektstruktur:

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

Hinweise für Mitwirkende, auch für KI-Agenten, stehen in [CLAUDE.md](CLAUDE.md).

*Das Wissen ist Macht. Bewahre es gut. Ave Omnissiah.*
