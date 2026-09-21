"""Prüft die Übersetzung zwischen Jev-API und Domäne."""

from __future__ import annotations

import pytest
from typesafe_sdk import SystemOneResponse

from routing.domain import Queue, UrgencyLevel
from routing.jev_client import (
    FRAGE_DRINGLICHKEIT,
    FRAGE_ESKALATION,
    FRAGE_QUEUE,
    baue_fragen,
    zu_entscheidung,
)


def test_fragen_decken_alle_warteschlangen_ab() -> None:
    fragen = baue_fragen()
    assert set(fragen) == {FRAGE_QUEUE, FRAGE_DRINGLICHKEIT, FRAGE_ESKALATION}
    assert set(fragen[FRAGE_QUEUE].criteria) == {queue.value for queue in Queue}


def test_dringlichkeitsfrage_nennt_so_viele_stufen_wie_die_domaene() -> None:
    fragen = baue_fragen()
    assert len(fragen[FRAGE_DRINGLICHKEIT].criteria) == len(list(UrgencyLevel))


def test_antwort_wird_zur_entscheidung(ticket, jev_antwort) -> None:
    entscheidung = zu_entscheidung(ticket, jev_antwort)

    assert entscheidung.ticket is ticket
    assert entscheidung.queue is Queue.ABRECHNUNG
    assert entscheidung.queue_konfidenz == pytest.approx(0.97)
    assert entscheidung.queue_verteilung[Queue.TECHNIK] == pytest.approx(0.02)
    assert entscheidung.dringlichkeit.stufe is UrgencyLevel.DRINGEND
    assert entscheidung.eskalationswahrscheinlichkeit == pytest.approx(0.37)


def test_verteilung_nutzt_die_warteschlangen_der_domaene(ticket, jev_antwort) -> None:
    entscheidung = zu_entscheidung(ticket, jev_antwort)
    assert set(entscheidung.queue_verteilung) == set(Queue)
    assert sum(entscheidung.queue_verteilung.values()) == pytest.approx(1.0)


def test_falscher_antworttyp_wird_gemeldet(ticket, jev_antwort) -> None:
    verdreht = jev_antwort.model_dump()
    verdreht["answers"][FRAGE_QUEUE] = {"type": "noul", "noul": 0.5}
    antwort = SystemOneResponse.model_validate(verdreht)

    with pytest.raises(TypeError, match=FRAGE_QUEUE):
        zu_entscheidung(ticket, antwort)
