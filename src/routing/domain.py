"""Das Domänenmodell des Ticket-Routings.

Die Begriffe hier folgen der Fachsprache des Kundenservice. Über die Jev-API
weiß dieses Modul nichts; die Übersetzung leistet `routing.jev_client`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Queue(StrEnum):
    """Die Warteschlange, die ein Ticket bearbeitet."""

    ABRECHNUNG = "abrechnung"
    TECHNIK = "technik"
    VERTRIEB = "vertrieb"
    VERTRAGSWESEN = "vertragswesen"

    @property
    def beschreibung(self) -> str:
        """Fachliche Abgrenzung der Warteschlange, auch Grundlage der Jev-Kriterien."""
        return _QUEUE_BESCHREIBUNGEN[self]


_QUEUE_BESCHREIBUNGEN: dict[Queue, str] = {
    Queue.ABRECHNUNG: (
        "Rechnungen, Zahlungen, Lastschriften, Mahnungen, Gutschriften, "
        "Erstattungen und alles, was einen Betrag betrifft."
    ),
    Queue.TECHNIK: (
        "Störungen, Fehlermeldungen, Ausfälle, Anmeldung und Zugang, "
        "Gerätetausch, Anschluss und Leitung."
    ),
    Queue.VERTRIEB: (
        "Preise, Tarifwechsel, Angebote, Zusatzleistungen, Neuverträge "
        "und Rückgewinnung von Interessenten."
    ),
    Queue.VERTRAGSWESEN: (
        "Kündigung, Widerruf, Laufzeit, Umzug, Vertragsübernahme, "
        "Datenauskunft und Stammdaten."
    ),
}


class UrgencyLevel(StrEnum):
    """Die vier Dringlichkeitsstufen in aufsteigender Reihenfolge."""

    ROUTINE = "Routine"
    BALD = "Bald"
    DRINGEND = "Dringend"
    SOFORT = "Sofort"

    @property
    def stufe(self) -> int:
        """Rang der Stufe, beginnend bei null."""
        return list(UrgencyLevel).index(self)

    @classmethod
    def aus_stufe(cls, stufe: int) -> UrgencyLevel:
        """Bildet einen Rang auf die Stufe ab und hält ihn im gültigen Bereich."""
        stufen = list(cls)
        return stufen[max(0, min(stufe, len(stufen) - 1))]


@dataclass(frozen=True, slots=True)
class Urgency:
    """Wie eilig ein Ticket ist, samt der Sicherheit dieser Einschätzung.

    `wert` trägt die Zwischenstufen, etwa 2.4 zwischen Dringend und Sofort.
    `stufe` rundet auf die nächstgelegene benannte Stufe.
    """

    wert: float
    konfidenz: float

    @property
    def stufe(self) -> UrgencyLevel:
        return UrgencyLevel.aus_stufe(round(self.wert))

    def __str__(self) -> str:
        return f"{self.stufe} ({self.wert:.1f})"


class MoodLevel(StrEnum):
    """Der Ton, in dem ein Kunde schreibt, in aufsteigender Schärfe."""

    SACHLICH = "Sachlich"
    ANGESPANNT = "Angespannt"
    VERAERGERT = "Verärgert"
    AUFGEBRACHT = "Aufgebracht"

    @property
    def stufe(self) -> int:
        """Rang der Stufe, beginnend bei null."""
        return list(MoodLevel).index(self)

    @classmethod
    def aus_stufe(cls, stufe: int) -> MoodLevel:
        """Bildet einen Rang auf die Stufe ab und hält ihn im gültigen Bereich."""
        stufen = list(cls)
        return stufen[max(0, min(stufe, len(stufen) - 1))]


@dataclass(frozen=True, slots=True)
class Mood:
    """Die Stimmung des Textes, getrennt von der Sachlage des Anliegens.

    Der Ton sagt, wie der Kunde schreibt, die Dringlichkeit, wie eilig die
    Sache ist. Beide laufen auseinander: Ein Ausfall kann nüchtern gemeldet
    werden, eine Kleinigkeit im Zorn.
    """

    wert: float
    konfidenz: float

    @property
    def stufe(self) -> MoodLevel:
        return MoodLevel.aus_stufe(round(self.wert))

    def __str__(self) -> str:
        return f"{self.stufe} ({self.wert:.1f})"


@dataclass(frozen=True, slots=True)
class Ticket:
    """Ein eingegangenes Kundenanliegen im Rohzustand."""

    kennung: str
    betreff: str
    text: str
    eingang: datetime
    kanal: str = "E-Mail"

    @property
    def volltext(self) -> str:
        """Betreff und Text als eine Einheit, so wie Jev sie bewertet."""
        return f"Betreff: {self.betreff}\n\n{self.text}"


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    """Das Ergebnis einer Jev-Anfrage, übersetzt in die Fachsprache."""

    ticket: Ticket
    queue: Queue
    queue_konfidenz: float
    queue_verteilung: dict[Queue, float]
    dringlichkeit: Urgency
    stimmung: Mood
    eskalationswahrscheinlichkeit: float

    @property
    def zweitbeste_queue(self) -> tuple[Queue, float] | None:
        """Die stärkste Alternative zur gewählten Warteschlange."""
        alternativen = [
            (queue, anteil)
            for queue, anteil in self.queue_verteilung.items()
            if queue is not self.queue
        ]
        if not alternativen:
            return None
        return max(alternativen, key=lambda eintrag: eintrag[1])

    @property
    def ton_ueber_sache(self) -> float:
        """Wie weit der Ton über der Sachlage liegt.

        Ein Wert über null heißt: Der Kunde schreibt schärfer, als die Sache
        es verlangt. Ein Wert unter null heißt: Er bleibt ruhig, obwohl es
        brennt. Beides taugt als Hinweis für die Leitstelle.
        """
        return self.stimmung.wert - self.dringlichkeit.wert


@dataclass(frozen=True, slots=True)
class RoutingPolicy:
    """Die Regeln, nach denen der Kundenservice mit einer Entscheidung umgeht.

    Jev liefert kalibrierte Wahrscheinlichkeiten. Die Schwellen hier legen fest,
    ab wann die Zuordnung automatisch greift und wann ein Mensch draufschaut.
    """

    mindestkonfidenz: float = 0.80
    eskalationsschwelle: float = 0.60
    sofort_ab_stufe: UrgencyLevel = UrgencyLevel.DRINGEND

    def laeuft_automatisch(self, entscheidung: RoutingDecision) -> bool:
        """Die Zuordnung greift ohne Rückfrage, sobald Jev sicher genug ist."""
        return entscheidung.queue_konfidenz >= self.mindestkonfidenz

    def eskaliert(self, entscheidung: RoutingDecision) -> bool:
        """Ein Teamleiter sieht das Ticket, sobald ein Konflikt droht."""
        return entscheidung.eskalationswahrscheinlichkeit >= self.eskalationsschwelle

    def ist_eilig(self, entscheidung: RoutingDecision) -> bool:
        """Das Ticket wandert in die Eilbearbeitung."""
        return entscheidung.dringlichkeit.stufe.stufe >= self.sofort_ab_stufe.stufe

    def naechster_schritt(self, entscheidung: RoutingDecision) -> str:
        """Fasst zusammen, was mit dem Ticket geschieht."""
        if self.eskaliert(entscheidung):
            return "Eskalation an die Teamleitung"
        if not self.laeuft_automatisch(entscheidung):
            return "Sichtprüfung in der Leitstelle"
        if self.ist_eilig(entscheidung):
            return f"Eilbearbeitung in {entscheidung.queue}"
        return f"Regelbearbeitung in {entscheidung.queue}"
