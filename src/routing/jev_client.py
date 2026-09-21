"""Access to the Jev API and the translation into the domain model.

Jev is a System One model: it takes a state and answers typed questions with
calibrated probabilities. This module keeps the API vocabulary away from the
domain. The words `noul`, `choice` and `score` appear here and nowhere else.
"""

from __future__ import annotations

import os
import threading
from typing import Final

from typesafe_sdk import (
    Choice,
    ChoiceAnswer,
    Noul,
    NoulAnswer,
    Score,
    ScoreAnswer,
    SystemOneResponse,
    TypeSafeClient,
)

from routing.domain import (
    Mood,
    MoodLevel,
    Queue,
    RoutingDecision,
    Ticket,
    Urgency,
    UrgencyLevel,
)

DEFAULT_MODEL: Final = "jev-latest"

QUESTION_QUEUE: Final = "queue"
QUESTION_URGENCY: Final = "urgency"
QUESTION_MOOD: Final = "mood"
QUESTION_ESCALATION: Final = "escalation"


def build_questions() -> dict[str, Choice | Score | Noul]:
    """Build the four questions from the domain model.

    The criteria come from `Queue`, `UrgencyLevel` and `MoodLevel`. The domain
    therefore states what Jev decides on, and both sides stay in step. The
    wording stays German because the tickets are German.
    """
    return {
        QUESTION_QUEUE: Choice(
            instructions=(
                "Welches Team des Kundenservice bearbeitet dieses Ticket? "
                "Entscheide nach dem Anliegen, nicht nach dem Tonfall."
            ),
            criteria={queue.value: queue.description for queue in Queue},
        ),
        QUESTION_URGENCY: Score(
            instructions=(
                "Wie eilig braucht der Kunde eine Antwort? Wiege Geldverlust, "
                "Ausfall und Fristen stärker als die Lautstärke der Beschwerde."
            ),
            criteria=[
                "Routine: Auskunft oder Wunsch ohne Zeitdruck, Antwort binnen einer Woche genügt.",
                "Bald: Der Kunde wartet spürbar, Antwort binnen zwei Werktagen.",
                "Dringend: Geld fehlt, Leistung fällt aus oder eine Frist läuft, Antwort noch heute.",
                "Sofort: Der Betrieb des Kunden steht still oder eine Frist endet heute.",
            ],
        ),
        QUESTION_MOOD: Score(
            instructions=(
                "In welchem Ton schreibt der Kunde? Bewerte allein die Sprache, "
                "nicht die Schwere des Anliegens."
            ),
            criteria=[
                "Sachlich: nüchterne Schilderung, höfliche Anrede, keine Wertung.",
                "Angespannt: spürbare Ungeduld, Nachdruck, Hinweis auf Wartezeit.",
                "Verärgert: offene Kritik, Vorwürfe, Ausrufezeichen, Enttäuschung.",
                "Aufgebracht: Zorn, Drohung, Angriff auf Personen, Großbuchstaben.",
            ],
        ),
        QUESTION_ESCALATION: Noul(
            instructions=(
                "Braucht dieses Ticket die Teamleitung, weil ein Konflikt droht?"
            ),
            criteria={
                "true": (
                    "Der Kunde droht mit Kündigung, Anwalt, Presse oder Aufsichtsbehörde, "
                    "beruft sich auf Recht und Gesetz oder beschwert sich über eine "
                    "frühere Bearbeitung."
                ),
                "false": (
                    "Ein sachliches Anliegen, das die Warteschlange allein klärt, "
                    "auch wenn der Kunde verärgert schreibt."
                ),
            },
        ),
    }


def to_decision(ticket: Ticket, response: SystemOneResponse) -> RoutingDecision:
    """Translate a Jev answer into a routing decision."""
    queue_answer = response.answers[QUESTION_QUEUE]
    urgency_answer = response.answers[QUESTION_URGENCY]
    mood_answer = response.answers[QUESTION_MOOD]
    escalation_answer = response.answers[QUESTION_ESCALATION]

    if not isinstance(queue_answer, ChoiceAnswer):
        raise TypeError(f"Jev returned type {queue_answer.type} for {QUESTION_QUEUE}")
    if not isinstance(urgency_answer, ScoreAnswer):
        raise TypeError(f"Jev returned type {urgency_answer.type} for {QUESTION_URGENCY}")
    if not isinstance(mood_answer, ScoreAnswer):
        raise TypeError(f"Jev returned type {mood_answer.type} for {QUESTION_MOOD}")
    if not isinstance(escalation_answer, NoulAnswer):
        raise TypeError(
            f"Jev returned type {escalation_answer.type} for {QUESTION_ESCALATION}"
        )

    return RoutingDecision(
        ticket=ticket,
        queue=Queue(queue_answer.choice),
        queue_confidence=queue_answer.confidence,
        queue_distribution={
            Queue(name): share for name, share in queue_answer.probabilities.items()
        },
        urgency=Urgency(
            value=urgency_answer.score, confidence=urgency_answer.confidence
        ),
        mood=Mood(value=mood_answer.score, confidence=mood_answer.confidence),
        escalation_probability=escalation_answer.noul,
    )


class JevClassifier:
    """Asks Jev how to route a ticket.

    One call answers all four questions at once. That saves time and keeps the
    cost at a single reading of the ticket text.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        client: TypeSafeClient | None = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or TypeSafeClient(
            api_key=api_key or os.environ.get("TYPESAFE_API_KEY"),
            model=model,
        )
        self._questions = build_questions()
        self._counter_lock = threading.Lock()
        self.last_model: str | None = None
        self.input_tokens = 0
        self.calls = 0

    def classify(self, ticket: Ticket) -> RoutingDecision:
        """Rate one ticket and return the decision."""
        response = self._client.system_one(
            state=ticket.full_text, questions=self._questions
        )
        with self._counter_lock:
            self.last_model = response.model
            self.input_tokens += response.usage.input_tokens or 0
            self.calls += 1
        return to_decision(ticket, response)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> JevClassifier:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
