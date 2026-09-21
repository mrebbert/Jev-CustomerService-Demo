"""The domain model of ticket routing.

The vocabulary follows the language of a customer service department. This
module knows nothing about the Jev API; `routing.jev_client` does the
translation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Queue(StrEnum):
    """The team that works on a ticket."""

    BILLING = "billing"
    TECHNICAL = "technical"
    SALES = "sales"
    CONTRACTS = "contracts"

    @property
    def description(self) -> str:
        """What the team covers. Also feeds the Jev criteria."""
        return _QUEUE_DESCRIPTIONS[self]


_QUEUE_DESCRIPTIONS: dict[Queue, str] = {
    Queue.BILLING: (
        "Rechnungen, Zahlungen, Lastschriften, Mahnungen, Inkasso, Gutschriften, "
        "Erstattungen und alles, was einen Betrag betrifft."
    ),
    Queue.TECHNICAL: (
        "Störungen, Fehlermeldungen, Ausfälle, Anmeldung und Zugang, Einstellungen "
        "und Sperren am Anschluss, Gerätetausch, Anschluss und Leitung."
    ),
    Queue.SALES: (
        "Preise, Tarifwechsel, Angebote, Zusatzleistungen, Verfügbarkeit vor einem "
        "Abschluss, Neuverträge und Rückgewinnung von Interessenten."
    ),
    Queue.CONTRACTS: (
        "Kündigung, Widerruf, Laufzeit, Umzug, Vertragsübernahme, Datenauskunft, "
        "Werbewiderspruch und Stammdaten."
    ),
}


class UrgencyLevel(StrEnum):
    """The four urgency levels, ordered from calm to immediate."""

    ROUTINE = "Routine"
    SOON = "Soon"
    URGENT = "Urgent"
    IMMEDIATE = "Immediate"

    @property
    def rank(self) -> int:
        """Position of the level, starting at zero."""
        return list(UrgencyLevel).index(self)

    @classmethod
    def from_rank(cls, rank: int) -> UrgencyLevel:
        """Map a rank onto a level and keep it inside the valid range."""
        levels = list(cls)
        return levels[max(0, min(rank, len(levels) - 1))]


class MoodLevel(StrEnum):
    """The tone a customer writes in, ordered from calm to furious."""

    FACTUAL = "Factual"
    TENSE = "Tense"
    ANNOYED = "Annoyed"
    OUTRAGED = "Outraged"

    @property
    def rank(self) -> int:
        """Position of the level, starting at zero."""
        return list(MoodLevel).index(self)

    @classmethod
    def from_rank(cls, rank: int) -> MoodLevel:
        """Map a rank onto a level and keep it inside the valid range."""
        levels = list(cls)
        return levels[max(0, min(rank, len(levels) - 1))]


@dataclass(frozen=True, slots=True)
class Urgency:
    """How fast a ticket needs an answer, plus how sure that reading is.

    `value` carries the steps in between, say 2.4 between Urgent and Immediate.
    `level` rounds to the nearest named level.
    """

    value: float
    confidence: float

    @property
    def level(self) -> UrgencyLevel:
        return UrgencyLevel.from_rank(round(self.value))

    def __str__(self) -> str:
        return f"{self.level} ({self.value:.1f})"


@dataclass(frozen=True, slots=True)
class Mood:
    """The tone of the text, kept apart from the substance of the request.

    Tone says how the customer writes, urgency says how pressing the matter is.
    The two drift apart: an outage may be reported calmly, a trifle in anger.
    """

    value: float
    confidence: float

    @property
    def level(self) -> MoodLevel:
        return MoodLevel.from_rank(round(self.value))

    def __str__(self) -> str:
        return f"{self.level} ({self.value:.1f})"


@dataclass(frozen=True, slots=True)
class Ticket:
    """An incoming customer request in its raw form.

    `expected_queue` holds the team a human assigned up front. It never reaches
    the model; it only serves to score the answers afterwards.
    """

    id: str
    subject: str
    body: str
    received_at: datetime
    channel: str = "E-Mail"
    expected_queue: Queue | None = None

    @property
    def full_text(self) -> str:
        """Subject and body as one unit, the way Jev reads them."""
        return f"Betreff: {self.subject}\n\n{self.body}"


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    """A Jev answer translated into the language of the department."""

    ticket: Ticket
    queue: Queue
    queue_confidence: float
    queue_distribution: dict[Queue, float]
    urgency: Urgency
    mood: Mood
    escalation_probability: float

    @property
    def runner_up(self) -> tuple[Queue, float] | None:
        """The strongest alternative to the chosen queue."""
        alternatives = [
            (queue, share)
            for queue, share in self.queue_distribution.items()
            if queue is not self.queue
        ]
        if not alternatives:
            return None
        return max(alternatives, key=lambda entry: entry[1])

    @property
    def tone_above_substance(self) -> float:
        """How far the tone sits above the substance.

        Above zero the customer writes sharper than the matter calls for. Below
        zero they stay calm although it burns. Both help the review desk.
        """
        return self.mood.value - self.urgency.value

    @property
    def matches_expectation(self) -> bool | None:
        """Whether the chosen queue meets the human assignment.

        Returns None when the ticket carries no expectation.
        """
        if self.ticket.expected_queue is None:
            return None
        return self.queue is self.ticket.expected_queue


@dataclass(frozen=True, slots=True)
class RoutingPolicy:
    """The rules the department applies to a decision.

    Jev returns calibrated probabilities. These thresholds decide when an
    assignment stands on its own and when a human takes a look.
    """

    min_confidence: float = 0.80
    escalation_threshold: float = 0.60
    rush_from_level: UrgencyLevel = UrgencyLevel.URGENT

    def runs_automatically(self, decision: RoutingDecision) -> bool:
        """The assignment stands as soon as Jev is sure enough."""
        return decision.queue_confidence >= self.min_confidence

    def escalates(self, decision: RoutingDecision) -> bool:
        """A team lead looks at the ticket as soon as a conflict looms."""
        return decision.escalation_probability >= self.escalation_threshold

    def is_rush(self, decision: RoutingDecision) -> bool:
        """The ticket moves into rush handling."""
        return decision.urgency.level.rank >= self.rush_from_level.rank

    def next_step(self, decision: RoutingDecision) -> str:
        """Sum up what happens to the ticket."""
        if self.escalates(decision):
            return "Escalation to the team lead"
        if not self.runs_automatically(decision):
            return "Review desk"
        if self.is_rush(decision):
            return f"Rush handling in {decision.queue}"
        return f"Standard handling in {decision.queue}"
