from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from main import chat
from servitor.agent import Agent
from servitor.config import Config
from servitor.llm import BackendBlockiert
from servitor.llm.fake import FakeBackend
from servitor.tools import erzeuge_werkzeuge

FERTIG = "FERTIG:\nErledigt.\nENDE"


def eingaben(*zeilen: str) -> Callable[[str], str]:
    """Liefert die Zeilen nacheinander und danach EOF (wie Strg+D)."""
    rest: Iterator[str] = iter(zeilen)

    def lies(_prompt: str) -> str:
        try:
            return next(rest)
        except StopIteration:
            raise EOFError from None

    return lies


@pytest.fixture
def agent_mit(tmp_path: Path) -> Callable[[FakeBackend], Agent]:
    werkzeuge = erzeuge_werkzeuge(tmp_path, lambda b, g: True, immer_fragen=False)
    return lambda backend: Agent(backend, werkzeuge, Config())


def test_chat_bearbeitet_mehrere_aufgaben(agent_mit: Callable[[FakeBackend], Agent]) -> None:
    backend = FakeBackend([FERTIG, FERTIG])
    code = chat(agent_mit(backend), ketzer=True, eingabe=eingaben("Aufgabe 1", "", "Aufgabe 2"))
    assert code == 0
    assert len(backend.prompts) == 2
    assert "Aufgabe 1" in backend.prompts[1]


def test_chat_endet_mit_ende_befehl(agent_mit: Callable[[FakeBackend], Agent]) -> None:
    backend = FakeBackend([])
    code = chat(agent_mit(backend), ketzer=False, eingabe=eingaben("/ende", "nie gesehen"))
    assert code == 0
    assert backend.prompts == []


def test_chat_neu_vergisst_kontext(agent_mit: Callable[[FakeBackend], Agent]) -> None:
    backend = FakeBackend([FERTIG, FERTIG])
    chat(agent_mit(backend), ketzer=True, eingabe=eingaben("Alt", "/neu", "Neu"))
    assert "Alt" not in backend.prompts[1]


def test_chat_stoppt_bei_captcha(agent_mit: Callable[[FakeBackend], Agent]) -> None:
    backend = FakeBackend([BackendBlockiert("CAPTCHA"), FERTIG])
    code = chat(agent_mit(backend), ketzer=True, eingabe=eingaben("x", "y"))
    assert code == 1
    assert len(backend.prompts) == 1
