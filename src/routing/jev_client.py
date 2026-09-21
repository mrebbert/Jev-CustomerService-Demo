"""Der Zugang zur Jev-API und die Übersetzung in das Domänenmodell.

Jev ist ein System-One-Modell: Es bekommt einen Zustand und beantwortet
typisierte Fragen mit kalibrierten Wahrscheinlichkeiten. Dieses Modul hält die
Begriffe der API von der Domäne fern. Nur hier stehen `noul`, `choice`, `score`.
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

STANDARDMODELL: Final = "jev-latest"

FRAGE_QUEUE: Final = "queue"
FRAGE_DRINGLICHKEIT: Final = "dringlichkeit"
FRAGE_STIMMUNG: Final = "stimmung"
FRAGE_ESKALATION: Final = "eskalation"


def baue_fragen() -> dict[str, Choice | Score | Noul]:
    """Erzeugt die drei Fragen aus dem Domänenmodell.

    Die Kriterien stammen aus `Queue` und `UrgencyLevel`. Damit beschreibt die
    Domäne, wonach Jev entscheidet, und beide Seiten bleiben gleichauf.
    """
    return {
        FRAGE_QUEUE: Choice(
            instructions=(
                "Welches Team des Kundenservice bearbeitet dieses Ticket? "
                "Entscheide nach dem Anliegen, nicht nach dem Tonfall."
            ),
            criteria={queue.value: queue.beschreibung for queue in Queue},
        ),
        FRAGE_DRINGLICHKEIT: Score(
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
        FRAGE_STIMMUNG: Score(
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
        FRAGE_ESKALATION: Noul(
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


def zu_entscheidung(ticket: Ticket, antwort: SystemOneResponse) -> RoutingDecision:
    """Übersetzt eine Jev-Antwort in eine Routing-Entscheidung."""
    queue_antwort = antwort.answers[FRAGE_QUEUE]
    dringlichkeit_antwort = antwort.answers[FRAGE_DRINGLICHKEIT]
    stimmung_antwort = antwort.answers[FRAGE_STIMMUNG]
    eskalation_antwort = antwort.answers[FRAGE_ESKALATION]

    if not isinstance(queue_antwort, ChoiceAnswer):
        raise TypeError(f"Jev lieferte für {FRAGE_QUEUE} den Typ {queue_antwort.type}")
    if not isinstance(dringlichkeit_antwort, ScoreAnswer):
        raise TypeError(
            f"Jev lieferte für {FRAGE_DRINGLICHKEIT} den Typ {dringlichkeit_antwort.type}"
        )
    if not isinstance(stimmung_antwort, ScoreAnswer):
        raise TypeError(
            f"Jev lieferte für {FRAGE_STIMMUNG} den Typ {stimmung_antwort.type}"
        )
    if not isinstance(eskalation_antwort, NoulAnswer):
        raise TypeError(
            f"Jev lieferte für {FRAGE_ESKALATION} den Typ {eskalation_antwort.type}"
        )

    return RoutingDecision(
        ticket=ticket,
        queue=Queue(queue_antwort.choice),
        queue_konfidenz=queue_antwort.confidence,
        queue_verteilung={
            Queue(name): anteil
            for name, anteil in queue_antwort.probabilities.items()
        },
        dringlichkeit=Urgency(
            wert=dringlichkeit_antwort.score,
            konfidenz=dringlichkeit_antwort.confidence,
        ),
        stimmung=Mood(
            wert=stimmung_antwort.score,
            konfidenz=stimmung_antwort.confidence,
        ),
        eskalationswahrscheinlichkeit=eskalation_antwort.noul,
    )


class JevClassifier:
    """Fragt Jev nach der Zuordnung eines Tickets.

    Ein Aufruf beantwortet alle drei Fragen zugleich. Das spart Zeit und hält
    die Kosten bei einer Bewertung des Ticketextes.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = STANDARDMODELL,
        client: TypeSafeClient | None = None,
    ) -> None:
        self._eigener_client = client is None
        self._client = client or TypeSafeClient(
            api_key=api_key or os.environ.get("TYPESAFE_API_KEY"),
            model=model,
        )
        self._fragen = baue_fragen()
        self._zaehlersperre = threading.Lock()
        self.letztes_modell: str | None = None
        self.token_eingang = 0

    def entscheide(self, ticket: Ticket) -> RoutingDecision:
        """Bewertet ein Ticket und liefert die Entscheidung."""
        antwort = self._client.system_one(state=ticket.volltext, questions=self._fragen)
        with self._zaehlersperre:
            self.letztes_modell = antwort.model
            self.token_eingang += antwort.usage.input_tokens or 0
        return zu_entscheidung(ticket, antwort)

    def close(self) -> None:
        if self._eigener_client:
            self._client.close()

    def __enter__(self) -> JevClassifier:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
