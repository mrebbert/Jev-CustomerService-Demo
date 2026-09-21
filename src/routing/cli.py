"""The entry point of the demo: load tickets, route them, show the outcome."""

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

from routing.domain import MoodLevel, Queue, RoutingPolicy, Ticket
from routing.jev_client import DEFAULT_MODEL, JevClassifier
from routing.router import RoutedTicket, RoutingRun, StabilityReport, TicketRouter
from routing.tickets import DEFAULT_SOURCE, load_tickets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRICE_PER_INPUT_TOKEN = 0.042 / 1_000_000

QUEUE_COLOR = {
    Queue.BILLING: "cyan",
    Queue.TECHNICAL: "green",
    Queue.SALES: "magenta",
    Queue.CONTRACTS: "yellow",
}

MOOD_COLOR = {
    MoodLevel.FACTUAL: "green",
    MoodLevel.TENSE: "yellow",
    MoodLevel.ANNOYED: "dark_orange",
    MoodLevel.OUTRAGED: "red",
}


def _plural(count: int) -> str:
    return "ticket" if count == 1 else "tickets"


def short_step(routed: RoutedTicket) -> str:
    """The column names the kind of handling; the queue sits next to it."""
    if routed.escalated:
        return "Escalation"
    if not routed.automatic:
        return "Review desk"
    if routed.rush:
        return "Rush handling"
    return "Standard handling"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="route-tickets",
        description="Routes customer service tickets to a team using the Jev model.",
    )
    parser.add_argument(
        "--file", type=Path, default=DEFAULT_SOURCE, help="YAML store of the tickets"
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="rate only the first N tickets"
    )
    parser.add_argument(
        "--ticket", action="append", default=[], help="a single id, repeatable"
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.80,
        help="from this confidence on the assignment skips the review desk",
    )
    parser.add_argument(
        "--escalation-threshold",
        type=float,
        default=0.60,
        help="from this probability on the ticket goes to the team lead",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="rate every ticket N times and report where the choice drifts",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Jev model id")
    parser.add_argument(
        "--json", action="store_true", help="print the result as JSON instead of a table"
    )
    return parser


def select_tickets(args: argparse.Namespace) -> list[Ticket]:
    tickets = load_tickets(args.file)
    if args.ticket:
        wanted = {ticket_id.upper() for ticket_id in args.ticket}
        tickets = [t for t in tickets if t.id.upper() in wanted]
        missing = wanted - {t.id.upper() for t in tickets}
        if missing:
            raise SystemExit(f"Unknown id: {', '.join(sorted(missing))}")
    if args.limit > 0:
        tickets = tickets[: args.limit]
    return tickets


def show_table(console: Console, run: RoutingRun) -> None:
    table = Table(title="Ticket assignment", header_style="bold")
    table.add_column("Id", no_wrap=True, min_width=7)
    table.add_column("Subject", max_width=38, min_width=14, no_wrap=True, overflow="ellipsis")
    table.add_column("Queue", no_wrap=True, min_width=10)
    table.add_column("Conf.", justify="right", min_width=5, no_wrap=True)
    table.add_column("Urgency", no_wrap=True, min_width=14)
    table.add_column("Mood", no_wrap=True, min_width=19)
    table.add_column("Esc.", justify="right", min_width=5, no_wrap=True)
    table.add_column("Step", no_wrap=True, min_width=17)
    table.add_column("Hit", justify="center", min_width=3, no_wrap=True)

    for routed in run.routed:
        decision = routed.decision
        confidence = f"{decision.queue_confidence:.0%}"
        if not routed.automatic:
            confidence = f"[bold red]{confidence}[/]"
        escalation = f"{decision.escalation_probability:.0%}"
        if routed.escalated:
            escalation = f"[bold red]{escalation}[/]"
        urgency = f"{decision.urgency.level} {decision.urgency.value:.1f}"
        if routed.rush:
            urgency = f"[bold]{urgency}[/]"
        mood = decision.mood
        mood_text = (
            f"[{MOOD_COLOR[mood.level]}]{mood.level} {mood.value:.1f}[/] "
            f"({mood.confidence:.0%})"
        )
        match decision.matches_expectation:
            case True:
                hit = "[green]yes[/]"
            case False:
                hit = f"[bold red]{decision.ticket.expected_queue}[/]"
            case _:
                hit = "[dim]·[/]"

        table.add_row(
            decision.ticket.id,
            decision.ticket.subject,
            f"[{QUEUE_COLOR[decision.queue]}]{decision.queue}[/]",
            confidence,
            urgency,
            mood_text,
            escalation,
            short_step(routed),
            hit,
        )
    console.print(table)


def show_summary(
    console: Console,
    run: RoutingRun,
    classifier: JevClassifier,
    stability: StabilityReport | None = None,
) -> None:
    queues = Counter(r.decision.queue for r in run.routed)
    moods = Counter(r.decision.mood.level for r in run.routed)
    steps = Counter(short_step(r) for r in run.routed)
    total = len(run.routed)

    lines = [
        "[bold]Queue load[/]",
        *(
            f"  {queue.value:<12} {count:>3} {_plural(count)}"
            for queue, count in sorted(queues.items(), key=lambda p: -p[1])
        ),
        "",
        "[bold]Tone[/]",
        *(
            f"  {level.value:<12} {count:>3} {_plural(count)}"
            for level, count in sorted(moods.items(), key=lambda p: p[0].rank)
        ),
        "",
        "[bold]Next step[/]",
        *(
            f"  {name:<18} {count:>3} of {total}"
            for name, count in sorted(steps.items(), key=lambda p: -p[1])
        ),
    ]

    hits = run.hit_rate
    if hits:
        correct, scored = hits
        lines += [
            "",
            "[bold]Against the human assignment[/]",
            f"  hits               {correct:>3} of {scored}  ({correct / scored:.0%})",
        ]
        misses = run.misses
        if misses:
            lines.append(f"  misses             {len(misses):>3}")
            for miss in sorted(misses, key=lambda m: m.decision.queue_confidence):
                lines.append(
                    f"    {miss.ticket.id}  {miss.decision.queue} instead of "
                    f"{miss.ticket.expected_queue}, confidence "
                    f"{miss.decision.queue_confidence:.0%}"
                )
        unscored = total - scored
        if unscored:
            lines.append(f"  without expectation {unscored:>2}")

    if stability and stability.runs > 1:
        drifting = stability.drifting
        lines += [
            "",
            f"[bold]Stability over {stability.runs} runs[/]",
            f"  same queue every time {stability.stable_count:>3} of {len(stability.queues_seen)}",
        ]
        for ticket_id, seen in sorted(drifting.items()):
            spread = ", ".join(f"{q}×{n}" for q, n in seen.most_common())
            lines.append(f"    {ticket_id}  {spread}")

    if run.failures:
        lines += [
            "",
            f"[bold red]Failed: {len(run.failures)}[/]",
            *(f"  {f.id}  {f.reason}" for f in run.failures),
        ]

    cost = classifier.input_tokens * PRICE_PER_INPUT_TOKEN
    lines += [
        "",
        f"Model:             {classifier.last_model}",
        f"Calls:             {classifier.calls}",
        f"Input tokens:      {classifier.input_tokens}",
        f"Cost:              {cost:.4f} USD",
    ]
    console.print("\n".join(lines))


def as_json(run: RoutingRun) -> str:
    data = [
        {
            "id": r.ticket.id,
            "subject": r.ticket.subject,
            "queue": r.decision.queue.value,
            "confidence": round(r.decision.queue_confidence, 4),
            "distribution": {
                queue.value: round(share, 4)
                for queue, share in r.decision.queue_distribution.items()
            },
            "urgency": {
                "level": r.decision.urgency.level.value,
                "value": round(r.decision.urgency.value, 2),
                "confidence": round(r.decision.urgency.confidence, 4),
            },
            "mood": {
                "level": r.decision.mood.level.value,
                "value": round(r.decision.mood.value, 2),
                "confidence": round(r.decision.mood.confidence, 4),
            },
            "tone_above_substance": round(r.decision.tone_above_substance, 2),
            "escalation_probability": round(r.decision.escalation_probability, 4),
            "next_step": r.next_step,
            "expected_queue": (
                r.ticket.expected_queue.value if r.ticket.expected_queue else None
            ),
            "hit": r.decision.matches_expectation,
        }
        for r in run.routed
    ]
    if run.failures:
        data.append({"failures": [{"id": f.id, "reason": f.reason} for f in run.failures]})
    return json.dumps(data, ensure_ascii=False, indent=2)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_dotenv(PROJECT_ROOT / ".env")
    console = Console()

    if not os.environ.get("TYPESAFE_API_KEY"):
        console.print(
            "[bold red]TYPESAFE_API_KEY is missing.[/] "
            "Put it into .env, the template sits in .env.example."
        )
        return 2

    tickets = select_tickets(args)
    if not tickets:
        console.print("No tickets to rate.")
        return 1

    policy = RoutingPolicy(
        min_confidence=args.min_confidence,
        escalation_threshold=args.escalation_threshold,
    )

    with JevClassifier(model=args.model) as classifier:
        router = TicketRouter(classifier, policy)
        passes = max(1, args.repeat)
        label = f"Jev rates {len(tickets)} tickets"
        with console.status(f"{label} ({passes}×) ..." if passes > 1 else f"{label} ..."):
            if passes > 1:
                run, stability = router.route_repeatedly(tickets, passes)
            else:
                run, stability = router.route_all(tickets), None

        if args.json:
            print(as_json(run))
            return 1 if run.failures else 0

        show_table(console, run)
        console.print()
        show_summary(console, run, classifier, stability)
    return 1 if run.failures else 0


if __name__ == "__main__":
    sys.exit(main())
