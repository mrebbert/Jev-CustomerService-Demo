"""Shared building blocks for the tests. No test talks to the Jev API."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from typesafe_sdk import SystemOneResponse

from routing.domain import Mood, Queue, RoutingDecision, Ticket, Urgency

RECORDINGS = Path(__file__).parent / "recordings"


def read_recording(name: str) -> SystemOneResponse:
    """Read a recorded Jev answer from a JSON file.

    The path runs through the JSON text, not through a dict loaded first: the
    SDK answer models validate strictly, and the level keys of a score answer
    count as numbers. In JSON mode Pydantic converts the format's strings into
    those numbers; from a dict it does not.
    """
    return SystemOneResponse.model_validate_json(
        (RECORDINGS / name).read_text(encoding="utf-8")
    )


@pytest.fixture
def ticket() -> Ticket:
    return Ticket(
        id="NT-0001",
        subject="Lastschrift zweimal abgebucht",
        body="Der Betrag wurde im September zweimal abgebucht.",
        received_at=datetime(2026, 9, 18, 8, 12),
        expected_queue=Queue.BILLING,
    )


@pytest.fixture
def jev_response() -> SystemOneResponse:
    """A real Jev answer, recorded on 21 September 2026."""
    return read_recording("jev_response.json")


def decision_with(
    ticket: Ticket,
    *,
    queue: Queue = Queue.BILLING,
    confidence: float = 0.97,
    urgency: float = 1.0,
    mood: float = 1.0,
    escalation: float = 0.05,
) -> RoutingDecision:
    """Build a decision for tests of the policy."""
    rest = (1.0 - confidence) / 3
    return RoutingDecision(
        ticket=ticket,
        queue=queue,
        queue_confidence=confidence,
        queue_distribution={q: (confidence if q is queue else rest) for q in Queue},
        urgency=Urgency(value=urgency, confidence=0.9),
        mood=Mood(value=mood, confidence=0.8),
        escalation_probability=escalation,
    )


def make_ticket(ticket_id: str, expected: Queue | None = None) -> Ticket:
    return Ticket(
        id=ticket_id,
        subject=f"Anliegen {ticket_id}",
        body="Beispieltext",
        received_at=datetime(2026, 9, 18, 9, 0),
        expected_queue=expected,
    )
