"""Checks the entry point without touching the network."""

from __future__ import annotations

import json

import pytest

from conftest import decision_with, make_ticket
from routing.cli import as_json, build_parser, select_tickets, short_step
from routing.domain import Queue, RoutingPolicy
from routing.router import RoutingFailure, RoutingRun, TicketRouter


class StubClassifier:
    def __init__(self, **kwargs) -> None:
        self._kwargs = kwargs

    def classify(self, ticket):
        return decision_with(ticket, **self._kwargs)


def route(ticket, **kwargs) -> RoutingRun:
    return TicketRouter(StubClassifier(**kwargs), RoutingPolicy()).route_all([ticket])


def parse(*argv: str):
    return build_parser().parse_args(list(argv))


def test_the_defaults_match_the_policy() -> None:
    args = parse()
    assert args.min_confidence == RoutingPolicy().min_confidence
    assert args.escalation_threshold == RoutingPolicy().escalation_threshold
    assert args.repeat == 1
    assert args.limit == 0


def test_the_ticket_option_repeats() -> None:
    args = parse("--ticket", "NT-2041", "--ticket", "NT-2042")
    assert args.ticket == ["NT-2041", "NT-2042"]


def test_the_limit_cuts_the_batch() -> None:
    tickets = select_tickets(parse("--limit", "5"))
    assert len(tickets) == 5
    assert tickets[0].id == "NT-2041"


def test_a_single_id_selects_one_ticket_case_insensitively() -> None:
    tickets = select_tickets(parse("--ticket", "nt-2047"))
    assert [t.id for t in tickets] == ["NT-2047"]


def test_an_unknown_id_stops_the_run() -> None:
    with pytest.raises(SystemExit, match="NT-9999"):
        select_tickets(parse("--ticket", "NT-9999"))


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"escalation": 0.9}, "Escalation"),
        ({"confidence": 0.4}, "Review desk"),
        ({"urgency": 2.5}, "Rush handling"),
        ({"urgency": 0.2}, "Standard handling"),
    ],
)
def test_the_short_step_follows_the_policy(kwargs, expected) -> None:
    run = route(make_ticket("NT-1", Queue.BILLING), **kwargs)
    assert short_step(run.routed[0]) == expected


def test_the_json_carries_every_field_of_a_decision() -> None:
    run = route(make_ticket("NT-1", Queue.BILLING), queue=Queue.BILLING, mood=2.0)
    entry = json.loads(as_json(run))[0]

    assert entry["id"] == "NT-1"
    assert entry["queue"] == "billing"
    assert entry["expected_queue"] == "billing"
    assert entry["hit"] is True
    assert entry["mood"]["level"] == "Annoyed"
    assert set(entry["distribution"]) == {q.value for q in Queue}
    assert entry["tone_above_substance"] == pytest.approx(1.0)


def test_the_json_marks_a_miss() -> None:
    run = route(make_ticket("NT-1", Queue.SALES), queue=Queue.BILLING)
    entry = json.loads(as_json(run))[0]
    assert entry["hit"] is False
    assert entry["expected_queue"] == "sales"


def test_the_json_lists_failures_last() -> None:
    run = route(make_ticket("NT-1", Queue.BILLING))
    run.failures.append(
        RoutingFailure(ticket=make_ticket("NT-2"), reason="TimeoutError: too slow")
    )
    entries = json.loads(as_json(run))

    assert entries[-1]["failures"] == [{"id": "NT-2", "reason": "TimeoutError: too slow"}]
