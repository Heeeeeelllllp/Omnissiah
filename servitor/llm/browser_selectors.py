"""Alle CSS-Selektoren für den Google KI-Modus an einer Stelle.

Google ändert die Seite häufig. Wenn der Adapter nichts mehr findet:
`python main.py --sichtbar "..."` starten, mit den DevTools nachsehen und
hier anpassen. Mehrere Alternativen werden mit Komma getrennt.
"""

KI_MODUS_URL = "https://www.google.com/ai"

# Buttons im Cookie-Banner ("Alle akzeptieren"); #L2AGLb ist die bekannte ID.
COOKIE_AKZEPTIEREN = "#L2AGLb, button:has-text('Alle akzeptieren'), button:has-text('Accept all')"

# Eingabefeld für den Prompt.
EINGABEFELD = "textarea[name='q'], textarea, div[contenteditable='true'][role='textbox']"

# Container der Modellantwort. Es wird jeweils der letzte Treffer gelesen.
ANTWORT = "div[data-subtree='aimc'], div[data-container-id='main-col']"

# Hinweis, dass Google den KI-Modus für diesen Browser sperrt (z. B. headless erkannt).
NICHT_VERFUEGBAR = "text=/KI-Modus ist derzeit .* nicht verfügbar|AI Mode (is|isn't) .*available/i"

# Hinweise auf CAPTCHA / Bot-Erkennung.
# Im KI-Modus erscheint das CAPTCHA als Dialog mit einem iframe auf /sorry/.
CAPTCHA = (
    "iframe[src*='recaptcha'], iframe[src*='/sorry/'], form#captcha-form, div#recaptcha, "
    "[role='dialog'][aria-label*='Captcha' i]"
)
CAPTCHA_URL_TEIL = "/sorry/"
