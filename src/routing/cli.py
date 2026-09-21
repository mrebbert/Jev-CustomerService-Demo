"""Der Einstieg für die Demo: Tickets laden, routen, Ergebnis zeigen."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from routing.domain import Queue, RoutingPolicy, Ticket
from routing.jev_client import STANDARDMODELL, JevClassifier
from routing.router import RoutedTicket, TicketRouter
from routing.tickets import STANDARDABLAGE, lade_tickets

PROJEKTWURZEL = Path(__file__).resolve().parents[2]

FARBE_JE_QUEUE = {
    Queue.ABRECHNUNG: "cyan",
    Queue.TECHNIK: "green",
    Queue.VERTRIEB: "magenta",
    Queue.VERTRAGSWESEN: "yellow",
}


def baue_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="route-tickets",
        description="Ordnet Kundenservice-Tickets mit dem Modell Jev einem Team zu.",
    )
    parser.add_argument(
        "--datei", type=Path, default=STANDARDABLAGE, help="YAML-Ablage der Tickets"
    )
    parser.add_argument(
        "--anzahl", type=int, default=0, help="nur die ersten N Tickets bewerten"
    )
    parser.add_argument(
        "--ticket", action="append", default=[], help="einzelne Kennung, mehrfach erlaubt"
    )
    parser.add_argument(
        "--mindestkonfidenz",
        type=float,
        default=0.80,
        help="ab dieser Konfidenz läuft die Zuordnung ohne Sichtprüfung",
    )
    parser.add_argument(
        "--eskalationsschwelle",
        type=float,
        default=0.60,
        help="ab dieser Wahrscheinlichkeit geht das Ticket an die Teamleitung",
    )
    parser.add_argument("--modell", default=STANDARDMODELL, help="Jev-Modellkennung")
    parser.add_argument(
        "--json", action="store_true", help="Ergebnis als JSON statt als Tabelle"
    )
    return parser


def waehle_tickets(args: argparse.Namespace) -> list[Ticket]:
    tickets = lade_tickets(args.datei)
    if args.ticket:
        gesucht = {kennung.upper() for kennung in args.ticket}
        tickets = [t for t in tickets if t.kennung.upper() in gesucht]
        fehlend = gesucht - {t.kennung.upper() for t in tickets}
        if fehlend:
            raise SystemExit(f"Unbekannte Kennung: {', '.join(sorted(fehlend))}")
    if args.anzahl > 0:
        tickets = tickets[: args.anzahl]
    return tickets


def zeige_tabelle(console: Console, ergebnisse: list[RoutedTicket]) -> None:
    tabelle = Table(title="Zuordnung der Tickets", header_style="bold")
    tabelle.add_column("Kennung", no_wrap=True, min_width=7)
    tabelle.add_column("Betreff", max_width=38, min_width=14, no_wrap=True, overflow="ellipsis")
    tabelle.add_column("Warteschlange", no_wrap=True, min_width=13)
    tabelle.add_column("Konf.", justify="right", min_width=5, no_wrap=True)
    tabelle.add_column("Dringlichkeit", no_wrap=True, min_width=14)
    tabelle.add_column("Eskal.", justify="right", min_width=6, no_wrap=True)
    tabelle.add_column("Nächster Schritt", no_wrap=True, overflow="ellipsis")

    for ergebnis in ergebnisse:
        entscheidung = ergebnis.entscheidung
        farbe = FARBE_JE_QUEUE[entscheidung.queue]
        konfidenz = f"{entscheidung.queue_konfidenz:.0%}"
        if not ergebnis.automatisch:
            konfidenz = f"[bold red]{konfidenz}[/]"
        eskalation = f"{entscheidung.eskalationswahrscheinlichkeit:.0%}"
        if ergebnis.eskaliert:
            eskalation = f"[bold red]{eskalation}[/]"
        dringlichkeit = str(entscheidung.dringlichkeit)
        if ergebnis.eilig:
            dringlichkeit = f"[bold]{dringlichkeit}[/]"

        tabelle.add_row(
            entscheidung.ticket.kennung,
            entscheidung.ticket.betreff,
            f"[{farbe}]{entscheidung.queue}[/]",
            konfidenz,
            dringlichkeit,
            eskalation,
            ergebnis.naechster_schritt,
        )
    console.print(tabelle)


def zeige_zusammenfassung(
    console: Console, ergebnisse: list[RoutedTicket], classifier: JevClassifier
) -> None:
    verteilung = Counter(e.entscheidung.queue for e in ergebnisse)
    sichtpruefung = sum(1 for e in ergebnisse if not e.automatisch)
    eskalationen = sum(1 for e in ergebnisse if e.eskaliert)
    eilig = sum(1 for e in ergebnisse if e.eilig)

    zeilen = [
        "[bold]Auslastung der Warteschlangen[/]",
        *(
            f"  {queue.value:<14} {anzahl:>2} Tickets"
            for queue, anzahl in sorted(verteilung.items(), key=lambda p: -p[1])
        ),
        "",
        f"Eilbearbeitung:    {eilig} von {len(ergebnisse)}",
        f"Eskalation:        {eskalationen} von {len(ergebnisse)}",
        f"Sichtprüfung:      {sichtpruefung} von {len(ergebnisse)}",
        f"Modell:            {classifier.letztes_modell}",
        f"Eingabe-Token:     {classifier.token_eingang}",
        f"Kosten:            {classifier.token_eingang * 0.042 / 1_000_000:.4f} USD",
    ]
    console.print("\n".join(zeilen))


def als_json(ergebnisse: list[RoutedTicket]) -> str:
    daten = [
        {
            "kennung": e.ticket.kennung,
            "betreff": e.ticket.betreff,
            "warteschlange": e.entscheidung.queue.value,
            "konfidenz": round(e.entscheidung.queue_konfidenz, 4),
            "verteilung": {
                queue.value: round(anteil, 4)
                for queue, anteil in e.entscheidung.queue_verteilung.items()
            },
            "dringlichkeit": {
                "stufe": e.entscheidung.dringlichkeit.stufe.value,
                "wert": round(e.entscheidung.dringlichkeit.wert, 2),
                "konfidenz": round(e.entscheidung.dringlichkeit.konfidenz, 4),
            },
            "eskalationswahrscheinlichkeit": round(
                e.entscheidung.eskalationswahrscheinlichkeit, 4
            ),
            "naechster_schritt": e.naechster_schritt,
        }
        for e in ergebnisse
    ]
    return json.dumps(daten, ensure_ascii=False, indent=2)


def main(argv: list[str] | None = None) -> int:
    args = baue_parser().parse_args(argv)
    load_dotenv(PROJEKTWURZEL / ".env")
    console = Console()

    if not os.environ.get("TYPESAFE_API_KEY"):
        console.print(
            "[bold red]TYPESAFE_API_KEY fehlt.[/] "
            "Lege ihn in .env ab, die Vorlage steht in .env.example."
        )
        return 2

    tickets = waehle_tickets(args)
    if not tickets:
        console.print("Keine Tickets zum Bewerten gefunden.")
        return 1

    policy = RoutingPolicy(
        mindestkonfidenz=args.mindestkonfidenz,
        eskalationsschwelle=args.eskalationsschwelle,
    )

    with JevClassifier(model=args.modell) as classifier:
        router = TicketRouter(classifier, policy)
        with console.status(f"Jev bewertet {len(tickets)} Tickets ..."):
            ergebnisse = router.route_alle(tickets)

        if args.json:
            print(als_json(ergebnisse))
            return 0

        zeige_tabelle(console, ergebnisse)
        console.print()
        zeige_zusammenfassung(console, ergebnisse, classifier)
    return 0


if __name__ == "__main__":
    sys.exit(main())
