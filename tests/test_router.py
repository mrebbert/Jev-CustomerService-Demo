"""Prüft den Anwendungsfall mit einer Attrappe statt der Jev-API."""

from __future__ import annotations

from datetime import datetime

from conftest import entscheidung_mit
from routing.domain import Queue, RoutingDecision, RoutingPolicy, Ticket
from routing.router import TicketRouter


class AttrappeClassifier:
    """Liefert vorgegebene Entscheidungen und zählt die Aufrufe."""

    def __init__(self, vorgaben: dict[str, RoutingDecision]) -> None:
        self._vorgaben = vorgaben
        self.aufrufe: list[str] = []

    def entscheide(self, ticket: Ticket) -> RoutingDecision:
        self.aufrufe.append(ticket.kennung)
        return self._vorgaben[ticket.kennung]


def baue_ticket(kennung: str) -> Ticket:
    return Ticket(
        kennung=kennung,
        betreff=f"Anliegen {kennung}",
        text="Beispieltext",
        eingang=datetime(2026, 9, 18, 9, 0),
    )


def test_router_wendet_die_richtlinie_an() -> None:
    ticket = baue_ticket("NT-1")
    classifier = AttrappeClassifier(
        {"NT-1": entscheidung_mit(ticket, queue=Queue.TECHNIK, dringlichkeit=2.6)}
    )
    ergebnis = TicketRouter(classifier).route(ticket)

    assert ergebnis.ticket is ticket
    assert ergebnis.automatisch
    assert ergebnis.eilig
    assert not ergebnis.eskaliert
    assert ergebnis.naechster_schritt == "Eilbearbeitung in technik"


def test_router_haelt_die_reihenfolge_der_tickets() -> None:
    tickets = [baue_ticket(f"NT-{nummer}") for nummer in range(1, 13)]
    classifier = AttrappeClassifier(
        {t.kennung: entscheidung_mit(t) for t in tickets}
    )
    ergebnisse = TicketRouter(classifier, parallel=4).route_alle(tickets)

    assert [e.ticket.kennung for e in ergebnisse] == [t.kennung for t in tickets]
    assert sorted(classifier.aufrufe) == sorted(t.kennung for t in tickets)


def test_strengere_richtlinie_schickt_mehr_in_die_sichtpruefung() -> None:
    ticket = baue_ticket("NT-1")
    classifier = AttrappeClassifier({"NT-1": entscheidung_mit(ticket, konfidenz=0.85)})

    locker = TicketRouter(classifier, RoutingPolicy(mindestkonfidenz=0.80))
    streng = TicketRouter(classifier, RoutingPolicy(mindestkonfidenz=0.95))

    assert locker.route(ticket).automatisch
    assert not streng.route(ticket).automatisch
