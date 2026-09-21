"""Checks the use case with a stub in place of the Jev API."""

from __future__ import annotations

import pytest

from conftest import decision_with, make_ticket
from routing.domain import Queue, RoutingDecision, RoutingPolicy, Ticket
from routing.router import TicketRouter


class StubClassifier:
    """Returns prepared decisions and counts the calls."""

    def __init__(self, decisions: dict[str, RoutingDecision]) -> None:
        self._decisions = decisions
        self.calls: list[str] = []

    def classify(self, ticket: Ticket) -> RoutingDecision:
        self.calls.append(ticket.id)
        return self._decisions[ticket.id]


class FailingClassifier:
    """Fails for the named tickets and answers for the rest."""

    def __init__(self, failing: set[str]) -> None:
        self._failing = failing

    def classify(self, ticket: Ticket) -> RoutingDecision:
        if ticket.id in self._failing:
            raise TimeoutError("the model did not answer in time")
        return decision_with(ticket)


class DriftingClassifier:
    """Hands out a different queue on every call for one ticket."""

    def __init__(self, drifting_id: str, queues: list[Queue]) -> None:
        self._drifting_id = drifting_id
        self._queues = queues
        self._seen = 0

    def classify(self, ticket: Ticket) -> RoutingDecision:
        if ticket.id != self._drifting_id:
            return decision_with(ticket, queue=Queue.BILLING)
        queue = self._queues[self._seen % len(self._queues)]
        self._seen += 1
        return decision_with(ticket, queue=queue, confidence=0.34)


def test_the_router_applies_the_policy() -> None:
    ticket = make_ticket("NT-1")
    classifier = StubClassifier(
        {"NT-1": decision_with(ticket, queue=Queue.TECHNICAL, urgency=2.6)}
    )
    routed = TicketRouter(classifier).route(ticket)

    assert routed.ticket is ticket
    assert routed.automatic
    assert routed.rush
    assert not routed.escalated
    assert routed.next_step == "Rush handling in technical"


def test_the_router_keeps_the_order_of_the_tickets() -> None:
    tickets = [make_ticket(f"NT-{number}") for number in range(1, 13)]
    classifier = StubClassifier({t.id: decision_with(t) for t in tickets})
    run = TicketRouter(classifier, parallel=4).route_all(tickets)

    assert [r.ticket.id for r in run.routed] == [t.id for t in tickets]
    assert sorted(classifier.calls) == sorted(t.id for t in tickets)
    assert not run.failures


def test_a_stricter_policy_sends_more_to_the_review_desk() -> None:
    ticket = make_ticket("NT-1")
    classifier = StubClassifier({"NT-1": decision_with(ticket, confidence=0.85)})

    lenient = TicketRouter(classifier, RoutingPolicy(min_confidence=0.80))
    strict = TicketRouter(classifier, RoutingPolicy(min_confidence=0.95))

    assert lenient.route(ticket).automatic
    assert not strict.route(ticket).automatic


def test_one_failing_ticket_leaves_the_rest_standing() -> None:
    tickets = [make_ticket(f"NT-{number}") for number in range(1, 6)]
    run = TicketRouter(FailingClassifier({"NT-3"}), parallel=2).route_all(tickets)

    assert len(run.routed) == 4
    assert [f.id for f in run.failures] == ["NT-3"]
    assert "TimeoutError" in run.failures[0].reason
    assert run.total == 5


def test_a_single_failing_ticket_is_reported() -> None:
    ticket = make_ticket("NT-1")
    run = TicketRouter(FailingClassifier({"NT-1"})).route_all([ticket])

    assert not run.routed
    assert run.failures[0].ticket is ticket


def test_an_empty_batch_produces_an_empty_run() -> None:
    run = TicketRouter(StubClassifier({})).route_all([])
    assert run.total == 0
    assert run.hit_rate is None


def test_the_hit_rate_counts_only_tickets_with_an_expectation() -> None:
    hit = make_ticket("NT-1", Queue.BILLING)
    miss = make_ticket("NT-2", Queue.SALES)
    unscored = make_ticket("NT-3")
    classifier = StubClassifier(
        {
            "NT-1": decision_with(hit, queue=Queue.BILLING),
            "NT-2": decision_with(miss, queue=Queue.TECHNICAL),
            "NT-3": decision_with(unscored, queue=Queue.BILLING),
        }
    )
    run = TicketRouter(classifier).route_all([hit, miss, unscored])

    assert run.hit_rate == (1, 2)
    assert [m.ticket.id for m in run.misses] == ["NT-2"]


def test_repeated_runs_name_the_drifting_ticket() -> None:
    steady = make_ticket("NT-1")
    drifting = make_ticket("NT-2")
    classifier = DriftingClassifier("NT-2", [Queue.SALES, Queue.TECHNICAL, Queue.SALES])
    router = TicketRouter(classifier, parallel=1)

    run, stability = router.route_repeatedly([steady, drifting], runs=3)

    assert stability.runs == 3
    assert stability.stable_count == 1
    assert set(stability.drifting) == {"NT-2"}
    assert stability.drifting["NT-2"][Queue.SALES] == 2
    assert len(run.routed) == 2


def test_a_single_run_reports_no_drift() -> None:
    tickets = [make_ticket("NT-1"), make_ticket("NT-2")]
    classifier = StubClassifier({t.id: decision_with(t) for t in tickets})
    _, stability = TicketRouter(classifier).route_repeatedly(tickets, runs=1)

    assert stability.runs == 1
    assert stability.drifting == {}
