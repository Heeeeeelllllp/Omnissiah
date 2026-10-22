"""CAPTCHA-Verhalten des Browser-Adapters – mit einer Fake-Seite, ohne echten Browser."""

from typing import Any

import pytest

from servitor.llm import BackendBlockiert
from servitor.llm.browser import BrowserBackend


class FakeSeite:
    """Simuliert eine Seite; `captcha` gibt pro Prüfung an, ob ein CAPTCHA sichtbar ist."""

    def __init__(self, captcha: list[bool], url: str = "https://www.google.com/search?udm=50"):
        self._captcha = captcha
        self.url = url

    def locator(self, selektor: str) -> "FakeSeite":
        return self

    def filter(self, **kwargs: Any) -> "FakeSeite":
        return self

    def count(self) -> int:
        aktiv = self._captcha.pop(0) if len(self._captcha) > 1 else self._captcha[0]
        return 1 if aktiv else 0

    def wait_for_timeout(self, ms: float) -> None:
        pass

    def is_closed(self) -> bool:
        return False


def backend(sichtbar: bool, wartezeit: float = 5.0) -> tuple[BrowserBackend, list[str]]:
    meldungen: list[str] = []
    b = BrowserBackend(
        sichtbar=sichtbar,
        captcha_wartezeit=wartezeit,
        bei_captcha=lambda: meldungen.append("captcha"),
    )
    return b, meldungen


def test_ohne_captcha_wird_nicht_gewartet() -> None:
    b, meldungen = backend(sichtbar=True)
    assert b._pruefe_blockade(FakeSeite([False])) == 0.0  # type: ignore[arg-type]
    assert meldungen == []


def test_ohne_fenster_bricht_captcha_ab() -> None:
    b, meldungen = backend(sichtbar=False)
    with pytest.raises(BackendBlockiert, match="--sichtbar"):
        b._pruefe_blockade(FakeSeite([True]))  # type: ignore[arg-type]
    assert meldungen == []


def test_sorry_seite_ohne_fenster_bricht_ab() -> None:
    b, _ = backend(sichtbar=False)
    seite = FakeSeite([False], url="https://www.google.com/sorry/index?continue=x")
    with pytest.raises(BackendBlockiert):
        b._pruefe_blockade(seite)  # type: ignore[arg-type]


def test_mit_fenster_wird_auf_den_menschen_gewartet() -> None:
    b, meldungen = backend(sichtbar=True)
    seite = FakeSeite([True, True, True, False])
    gewartet = b._pruefe_blockade(seite)  # type: ignore[arg-type]
    assert gewartet >= 0.0
    assert meldungen == ["captcha"]


def test_mit_fenster_bricht_nach_wartezeit_ab() -> None:
    b, meldungen = backend(sichtbar=True, wartezeit=0.05)
    with pytest.raises(BackendBlockiert, match="nicht innerhalb"):
        b._pruefe_blockade(FakeSeite([True]))  # type: ignore[arg-type]
    assert meldungen == ["captcha"]
