"""Checks the ticket store. A broken entry must fail before the first API call."""

from __future__ import annotations

import pytest

from routing.domain import Queue
from routing.tickets import DEFAULT_SOURCE, load_tickets

TICKETS = load_tickets()


def test_the_store_holds_a_hundred_tickets() -> None:
    assert len(TICKETS) == 100


def test_every_id_appears_once() -> None:
    ids = [t.id for t in TICKETS]
    assert len(set(ids)) == len(ids)


def test_every_ticket_carries_subject_and_body() -> None:
    for ticket in TICKETS:
        assert ticket.subject.strip(), f"{ticket.id} has no subject"
        assert len(ticket.body) > 40, f"{ticket.id} has almost no body"


def test_the_tickets_arrive_in_chronological_order() -> None:
    stamps = [t.received_at for t in TICKETS]
    assert stamps == sorted(stamps)


def test_every_queue_appears_in_the_gold_standard() -> None:
    expected = {t.expected_queue for t in TICKETS if t.expected_queue}
    assert expected == set(Queue)


def test_almost_every_ticket_carries_an_expectation() -> None:
    without = [t.id for t in TICKETS if t.expected_queue is None]
    assert without == ["NT-2074", "NT-2121", "NT-2124"]


def test_a_missing_field_names_the_ticket(tmp_path) -> None:
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        "tickets:\n"
        "  - id: NT-9001\n"
        "    subject: Ohne Text\n"
        '    received_at: "2026-09-18T08:00:00"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="NT-9001|body"):
        load_tickets(broken)


def test_an_unknown_queue_is_rejected(tmp_path) -> None:
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        "tickets:\n"
        "  - id: NT-9002\n"
        "    expected: hausmeisterei\n"
        "    subject: Falsche Warteschlange\n"
        '    received_at: "2026-09-18T08:00:00"\n'
        "    body: |\n"
        "      Ein Text, der lang genug ist, um die Pruefung zu bestehen.\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="NT-9002"):
        load_tickets(broken)


def test_the_default_source_is_the_store_in_the_repository() -> None:
    assert DEFAULT_SOURCE.name == "tickets.yaml"
    assert DEFAULT_SOURCE.exists()
