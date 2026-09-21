"""Prüft das Domänenmodell und die Richtlinie."""

from __future__ import annotations

import pytest

from conftest import entscheidung_mit
from routing.domain import Queue, RoutingPolicy, Urgency, UrgencyLevel


def test_jede_warteschlange_hat_eine_beschreibung() -> None:
    for queue in Queue:
        assert queue.beschreibung.strip()


@pytest.mark.parametrize(
    ("wert", "erwartet"),
    [
        (0.0, UrgencyLevel.ROUTINE),
        (0.4, UrgencyLevel.ROUTINE),
        (1.6, UrgencyLevel.DRINGEND),
        (2.01, UrgencyLevel.DRINGEND),
        (3.0, UrgencyLevel.SOFORT),
    ],
)
def test_dringlichkeit_rundet_auf_die_naechste_stufe(
    wert: float, erwartet: UrgencyLevel
) -> None:
    assert Urgency(wert=wert, konfidenz=0.9).stufe is erwartet


def test_stufe_bleibt_im_gueltigen_bereich() -> None:
    assert UrgencyLevel.aus_stufe(-3) is UrgencyLevel.ROUTINE
    assert UrgencyLevel.aus_stufe(99) is UrgencyLevel.SOFORT


def test_zweitbeste_queue_nennt_die_staerkste_alternative(ticket) -> None:
    entscheidung = entscheidung_mit(ticket, queue=Queue.ABRECHNUNG, konfidenz=0.70)
    zweitbeste = entscheidung.zweitbeste_queue
    assert zweitbeste is not None
    assert zweitbeste[0] is not Queue.ABRECHNUNG


def test_sichere_zuordnung_laeuft_automatisch(ticket) -> None:
    policy = RoutingPolicy(mindestkonfidenz=0.80)
    sicher = entscheidung_mit(ticket, konfidenz=0.95)
    unsicher = entscheidung_mit(ticket, konfidenz=0.55)
    assert policy.laeuft_automatisch(sicher)
    assert not policy.laeuft_automatisch(unsicher)
    assert policy.naechster_schritt(unsicher) == "Sichtprüfung in der Leitstelle"


def test_eskalation_geht_der_dringlichkeit_vor(ticket) -> None:
    policy = RoutingPolicy()
    entscheidung = entscheidung_mit(ticket, dringlichkeit=3.0, eskalation=0.88)
    assert policy.eskaliert(entscheidung)
    assert policy.ist_eilig(entscheidung)
    assert policy.naechster_schritt(entscheidung) == "Eskalation an die Teamleitung"


def test_eilige_tickets_gehen_in_die_eilbearbeitung(ticket) -> None:
    policy = RoutingPolicy()
    entscheidung = entscheidung_mit(ticket, queue=Queue.TECHNIK, dringlichkeit=2.4)
    assert policy.naechster_schritt(entscheidung) == "Eilbearbeitung in technik"


def test_ruhige_tickets_laufen_im_regelbetrieb(ticket) -> None:
    policy = RoutingPolicy()
    entscheidung = entscheidung_mit(ticket, dringlichkeit=0.3)
    assert policy.naechster_schritt(entscheidung) == "Regelbearbeitung in abrechnung"


def test_volltext_traegt_betreff_und_text(ticket) -> None:
    assert ticket.betreff in ticket.volltext
    assert ticket.text in ticket.volltext
