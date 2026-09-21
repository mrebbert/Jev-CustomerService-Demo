"""The use case: rate tickets and determine the next step."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Protocol

from routing.domain import Queue, RoutingDecision, RoutingPolicy, Ticket


class TicketClassifier(Protocol):
    """The port the routing asks for a verdict.

    The demo uses `routing.jev_client.JevClassifier`. Tests plug in stubs that
    return prepared decisions and run without the network.
    """

    def classify(self, ticket: Ticket) -> RoutingDecision: ...


@dataclass(frozen=True, slots=True)
class RoutedTicket:
    """A decision plus what the policy concludes from it."""

    decision: RoutingDecision
    next_step: str
    automatic: bool
    escalated: bool
    rush: bool

    @property
    def ticket(self) -> Ticket:
        return self.decision.ticket


@dataclass(frozen=True, slots=True)
class RoutingFailure:
    """A ticket the model could not rate.

    The run carries on. A single timeout must not cost the whole batch.
    """

    ticket: Ticket
    reason: str

    @property
    def id(self) -> str:
        return self.ticket.id


@dataclass(frozen=True, slots=True)
class RoutingRun:
    """Everything one pass over a batch of tickets produced."""

    routed: list[RoutedTicket] = field(default_factory=list)
    failures: list[RoutingFailure] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.routed) + len(self.failures)

    @property
    def hit_rate(self) -> tuple[int, int] | None:
        """Hits and scored tickets, counting only tickets with an expectation.

        Returns None when no ticket in the batch carries one.
        """
        scored = [r for r in self.routed if r.decision.matches_expectation is not None]
        if not scored:
            return None
        hits = sum(1 for r in scored if r.decision.matches_expectation)
        return hits, len(scored)

    @property
    def misses(self) -> list[RoutedTicket]:
        """Tickets whose queue differs from the human assignment."""
        return [r for r in self.routed if r.decision.matches_expectation is False]


@dataclass(frozen=True, slots=True)
class StabilityReport:
    """How far repeated runs over the same tickets agree."""

    runs: int
    queues_seen: dict[str, Counter[Queue]]

    @property
    def drifting(self) -> dict[str, Counter[Queue]]:
        """Tickets that landed in more than one queue."""
        return {
            ticket_id: seen
            for ticket_id, seen in self.queues_seen.items()
            if len(seen) > 1
        }

    @property
    def stable_count(self) -> int:
        return len(self.queues_seen) - len(self.drifting)


class TicketRouter:
    """Joins the model's verdict with the rules of the department."""

    def __init__(
        self,
        classifier: TicketClassifier,
        policy: RoutingPolicy | None = None,
        *,
        parallel: int = 8,
    ) -> None:
        self._classifier = classifier
        self._policy = policy or RoutingPolicy()
        self._parallel = max(1, parallel)

    @property
    def policy(self) -> RoutingPolicy:
        return self._policy

    def route(self, ticket: Ticket) -> RoutedTicket:
        """Rate one ticket and apply the policy. Errors travel to the caller."""
        decision = self._classifier.classify(ticket)
        return RoutedTicket(
            decision=decision,
            next_step=self._policy.next_step(decision),
            automatic=self._policy.runs_automatically(decision),
            escalated=self._policy.escalates(decision),
            rush=self._policy.is_rush(decision),
        )

    def _route_safely(self, ticket: Ticket) -> RoutedTicket | RoutingFailure:
        try:
            return self.route(ticket)
        except Exception as error:  # the run carries on, the reason is reported
            return RoutingFailure(ticket=ticket, reason=f"{type(error).__name__}: {error}")

    def route_all(self, tickets: Iterable[Ticket]) -> RoutingRun:
        """Rate several tickets side by side and keep their order.

        A ticket that fails lands in `failures`; the rest of the batch stands.
        """
        inbox: Sequence[Ticket] = list(tickets)
        if not inbox:
            return RoutingRun()
        if len(inbox) == 1:
            results = [self._route_safely(inbox[0])]
        else:
            with ThreadPoolExecutor(max_workers=self._parallel) as pool:
                results = list(pool.map(self._route_safely, inbox))

        run = RoutingRun()
        for result in results:
            if isinstance(result, RoutedTicket):
                run.routed.append(result)
            else:
                run.failures.append(result)
        return run

    def route_repeatedly(
        self, tickets: Iterable[Ticket], runs: int
    ) -> tuple[RoutingRun, StabilityReport]:
        """Rate the same tickets several times and report where the choice drifts.

        The first pass is the result that counts. The further passes only serve
        to show which assignments the model keeps and which ones wander.
        """
        inbox = list(tickets)
        passes = [self.route_all(inbox) for _ in range(max(1, runs))]

        queues_seen: dict[str, Counter[Queue]] = {t.id: Counter() for t in inbox}
        for run in passes:
            for routed in run.routed:
                queues_seen[routed.ticket.id][routed.decision.queue] += 1

        report = StabilityReport(
            runs=len(passes),
            queues_seen={k: v for k, v in queues_seen.items() if v},
        )
        return passes[0], report
