"""Playwright-Adapter für den Google KI-Modus.

Spielregeln: nicht eingeloggt, frisches Profil, mindestens 5 s Pause zwischen
Anfragen, keine Parallelisierung und keine Umgehung von CAPTCHAs. Ein CAPTCHA
darf nur der Mensch im sichtbaren Fenster lösen.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from types import TracebackType

from playwright.sync_api import Browser, Page, Playwright, sync_playwright
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from servitor.config import MIN_PAUSE_SEKUNDEN
from servitor.llm import BackendBlockiert, BackendFehler
from servitor.llm import browser_selectors as sel

logger = logging.getLogger(__name__)

ABFRAGE_INTERVALL_MS = 500
SEITE_TIMEOUT_MS = 30_000
COOKIE_TIMEOUT_MS = 3_000
CAPTCHA_INTERVALL_MS = 1_000


class BrowserBackend:
    def __init__(
        self,
        sichtbar: bool = False,
        pause_sekunden: float = MIN_PAUSE_SEKUNDEN,
        antwort_timeout: float = 90.0,
        stabil_sekunden: float = 2.0,
        captcha_wartezeit: float = 300.0,
        bei_captcha: Callable[[], None] | None = None,
    ) -> None:
        self._sichtbar = sichtbar
        self._pause = max(MIN_PAUSE_SEKUNDEN, pause_sekunden)
        self._antwort_timeout = antwort_timeout
        self._stabil = stabil_sekunden
        self._captcha_wartezeit = captcha_wartezeit
        self._bei_captcha = bei_captcha
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._seite: Page | None = None
        self._letzte_anfrage: float | None = None
        self._cookies_erledigt = False

    def __enter__(self) -> BrowserBackend:
        self.starten()
        return self

    def __exit__(
        self,
        typ: type[BaseException] | None,
        wert: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.schliessen()

    def starten(self) -> None:
        self._playwright = sync_playwright().start()
        try:
            self._browser = self._playwright.chromium.launch(headless=not self._sichtbar)
        except PlaywrightError as fehler:
            self.schliessen()
            raise BackendFehler(
                "Chromium konnte nicht gestartet werden. Läuft das richtige Python "
                "(.venv aktiviert?) und wurde 'playwright install chromium' ausgeführt?\n"
                f"{fehler.message}"
            ) from fehler
        kontext = self._browser.new_context(locale="de-DE")  # frisches Profil, kein Login
        self._seite = kontext.new_page()
        self._seite.set_default_timeout(SEITE_TIMEOUT_MS)

    def schliessen(self) -> None:
        """Räumt auf – auch wenn der Nutzer das Fenster schon geschlossen hat."""
        try:
            if self._browser is not None:
                self._browser.close()
            if self._playwright is not None:
                self._playwright.stop()
        except PlaywrightError as fehler:
            logger.debug("Fehler beim Schließen des Browsers ignoriert: %s", fehler)
        self._browser = None
        self._playwright = None
        self._seite = None

    def frage(self, prompt: str) -> str:
        seite = self._aktive_seite()
        self._warte_auf_pause()
        try:
            seite.goto(sel.KI_MODUS_URL)
            self._pruefe_blockade(seite)
            self._bestaetige_cookies(seite)
            self._pruefe_blockade(seite)
            self._pruefe_verfuegbarkeit(seite)
            self._sende_prompt(seite, prompt)
            return self._warte_auf_antwort(seite)
        except PlaywrightTimeout as fehler:
            raise BackendFehler(f"Seite reagiert nicht: {fehler.message}") from fehler
        except PlaywrightError as fehler:
            raise BackendFehler(
                f"Browser nicht mehr erreichbar (Fenster geschlossen?): {fehler.message}"
            ) from fehler
        finally:
            self._letzte_anfrage = time.monotonic()

    def _aktive_seite(self) -> Page:
        if self._seite is None:
            raise BackendFehler("Browser wurde nicht gestartet.")
        return self._seite

    def _warte_auf_pause(self) -> None:
        if self._letzte_anfrage is None:
            return
        rest = self._pause - (time.monotonic() - self._letzte_anfrage)
        if rest > 0:
            logger.debug("Warte %.1f s bis zur nächsten Anfrage", rest)
            time.sleep(rest)

    def _bestaetige_cookies(self, seite: Page) -> None:
        if self._cookies_erledigt:
            return
        self._cookies_erledigt = True
        try:
            seite.locator(sel.COOKIE_AKZEPTIEREN).first.click(timeout=COOKIE_TIMEOUT_MS)
            logger.info("Cookie-Banner bestätigt")
        except PlaywrightTimeout:
            logger.info("Kein Cookie-Banner gefunden")

    def _pruefe_blockade(self, seite: Page) -> float:
        """Prüft auf ein CAPTCHA. Gibt zurück, wie lange auf den Menschen gewartet wurde.

        Das CAPTCHA wird nie automatisch gelöst: Ohne Fenster wird abgebrochen,
        mit `--sichtbar` darf der Nutzer es selbst lösen.
        """
        if not _captcha_aktiv(seite):
            return 0.0
        if not self._sichtbar:
            raise BackendBlockiert(
                "Google zeigt ein CAPTCHA. Mit --sichtbar kannst du es selbst lösen."
            )
        return self._warte_auf_mensch(seite)

    def _warte_auf_mensch(self, seite: Page) -> float:
        logger.warning(
            "CAPTCHA erkannt – warte bis zu %g s auf den Nutzer", self._captcha_wartezeit
        )
        if self._bei_captcha is not None:
            self._bei_captcha()
        start = time.monotonic()
        while time.monotonic() - start < self._captcha_wartezeit:
            seite.wait_for_timeout(CAPTCHA_INTERVALL_MS)
            if seite.is_closed():
                raise BackendFehler("Browserfenster wurde geschlossen.")
            try:
                if not _captcha_aktiv(seite):
                    logger.info("CAPTCHA gelöst")
                    return time.monotonic() - start
            except PlaywrightError:
                continue  # Seite lädt nach dem Lösen gerade neu
        raise BackendBlockiert(
            f"Das CAPTCHA wurde nicht innerhalb von {self._captcha_wartezeit:g} s gelöst."
        )

    def _pruefe_verfuegbarkeit(self, seite: Page) -> None:
        """Nur vor dem Senden prüfen – eine Antwort darf den Text ja enthalten."""
        if seite.locator(sel.NICHT_VERFUEGBAR).count() > 0:
            raise BackendBlockiert(
                "Google meldet: Der KI-Modus ist für dieses Gerät nicht verfügbar "
                "(automatisierter Browser erkannt)."
            )

    def _sende_prompt(self, seite: Page, prompt: str) -> None:
        feld = seite.locator(sel.EINGABEFELD).first
        feld.wait_for(state="visible")
        feld.fill(prompt)
        feld.press("Enter")

    def _lies_antwort(self, seite: Page) -> str:
        antworten = seite.locator(sel.ANTWORT)
        if antworten.count() == 0:
            return ""
        return antworten.last.inner_text().strip()

    def _warte_auf_antwort(self, seite: Page) -> str:
        """Fertig ist die Antwort, wenn sich der Text `stabil_sekunden` nicht ändert."""
        ende = time.monotonic() + self._antwort_timeout
        letzter_text = ""
        stabil_seit = time.monotonic()
        while time.monotonic() < ende:
            ende += self._pruefe_blockade(seite)  # Wartezeit auf den Menschen zählt nicht mit
            text = self._lies_antwort(seite)
            jetzt = time.monotonic()
            if text != letzter_text:
                letzter_text = text
                stabil_seit = jetzt
            elif text and jetzt - stabil_seit >= self._stabil:
                return text
            seite.wait_for_timeout(ABFRAGE_INTERVALL_MS)
        raise BackendFehler(f"Keine fertige Antwort nach {self._antwort_timeout:g} s.")


def _captcha_aktiv(seite: Page) -> bool:
    if sel.CAPTCHA_URL_TEIL in seite.url:
        return True
    return seite.locator(sel.CAPTCHA).filter(visible=True).count() > 0
