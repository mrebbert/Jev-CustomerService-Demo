"""Der Anwendungsfall: Tickets bewerten und den nächsten Schritt bestimmen."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Protocol

from routing.domain import RoutingDecision, RoutingPolicy, Ticket


class TicketClassifier(Protocol):
    """Der Port, über den das Routing ein Urteil einholt.

    Die Demo nutzt `routing.jev_client.JevClassifier`. Tests setzen eine
    Attrappe mit aufgezeichneten Antworten ein und kommen ohne Netz aus.
    """

    def entscheide(self, ticket: Ticket) -> RoutingDecision: ...


@dataclass(frozen=True, slots=True)
class RoutedTicket:
    """Eine Entscheidung samt der Folgerungen aus der Richtlinie."""

    entscheidung: RoutingDecision
    naechster_schritt: str
    automatisch: bool
    eskaliert: bool
    eilig: bool

    @property
    def ticket(self) -> Ticket:
        return self.entscheidung.ticket


class TicketRouter:
    """Verbindet das Urteil des Modells mit den Regeln des Kundenservice."""

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
        """Bewertet ein Ticket und wendet die Richtlinie an."""
        entscheidung = self._classifier.entscheide(ticket)
        return RoutedTicket(
            entscheidung=entscheidung,
            naechster_schritt=self._policy.naechster_schritt(entscheidung),
            automatisch=self._policy.laeuft_automatisch(entscheidung),
            eskaliert=self._policy.eskaliert(entscheidung),
            eilig=self._policy.ist_eilig(entscheidung),
        )

    def route_alle(self, tickets: Iterable[Ticket]) -> list[RoutedTicket]:
        """Bewertet mehrere Tickets nebenläufig und hält ihre Reihenfolge."""
        posteingang: Sequence[Ticket] = list(tickets)
        if len(posteingang) == 1:
            return [self.route(posteingang[0])]
        with ThreadPoolExecutor(max_workers=self._parallel) as pool:
            return list(pool.map(self.route, posteingang))
