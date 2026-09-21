"""Gemeinsame Bausteine der Tests. Kein Test spricht mit der Jev-API."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from typesafe_sdk import SystemOneResponse

from routing.domain import Mood, Queue, RoutingDecision, Ticket, Urgency

AUFZEICHNUNGEN = Path(__file__).parent / "aufzeichnungen"


@pytest.fixture
def ticket() -> Ticket:
    return Ticket(
        kennung="NT-0001",
        betreff="Lastschrift zweimal abgebucht",
        text="Der Betrag wurde im September zweimal abgebucht.",
        eingang=datetime(2026, 9, 18, 8, 12),
    )


def lies_aufzeichnung(name: str) -> SystemOneResponse:
    """Liest eine aufgezeichnete Jev-Antwort aus einer JSON-Datei.

    Der Weg führt über den JSON-Text, nicht über ein vorher geladenes dict:
    Die Antwortmodelle des SDK prüfen streng, und die Stufenschlüssel einer
    Score-Antwort gelten als Zahlen. Im JSON-Modus rechnet Pydantic die
    Zeichenketten des Formats in diese Zahlen um, beim dict bleibt es dabei.
    """
    return SystemOneResponse.model_validate_json(
        (AUFZEICHNUNGEN / name).read_text("utf-8")
    )


@pytest.fixture
def jev_antwort() -> SystemOneResponse:
    """Eine echte Jev-Antwort, aufgezeichnet am 21.09.2026."""
    return lies_aufzeichnung("jev_antwort.json")


def entscheidung_mit(
    ticket: Ticket,
    *,
    queue: Queue = Queue.ABRECHNUNG,
    konfidenz: float = 0.97,
    dringlichkeit: float = 1.0,
    stimmung: float = 1.0,
    eskalation: float = 0.05,
) -> RoutingDecision:
    """Baut eine Entscheidung für Tests der Richtlinie."""
    rest = (1.0 - konfidenz) / 3
    return RoutingDecision(
        ticket=ticket,
        queue=queue,
        queue_konfidenz=konfidenz,
        queue_verteilung={q: (konfidenz if q is queue else rest) for q in Queue},
        dringlichkeit=Urgency(wert=dringlichkeit, konfidenz=0.9),
        stimmung=Mood(wert=stimmung, konfidenz=0.8),
        eskalationswahrscheinlichkeit=eskalation,
    )
