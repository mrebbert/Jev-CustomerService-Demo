"""Loads the demo tickets from the YAML store."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml

from routing.domain import Queue, Ticket

DEFAULT_SOURCE = Path(__file__).resolve().parents[2] / "data" / "tickets.yaml"


def load_tickets(source: Path | str = DEFAULT_SOURCE) -> list[Ticket]:
    """Read the tickets and return them in the order of the file.

    A malformed entry raises here, before a single call reaches the API.
    """
    raw = yaml.safe_load(Path(source).read_text(encoding="utf-8"))
    return [_to_ticket(entry, position) for position, entry in enumerate(raw["tickets"], 1)]


def _to_ticket(entry: dict, position: int) -> Ticket:
    try:
        expected = entry.get("expected")
        return Ticket(
            id=entry["id"],
            subject=entry["subject"],
            body=entry["body"].strip(),
            received_at=datetime.fromisoformat(entry["received_at"]),
            channel=entry.get("channel", "E-Mail"),
            expected_queue=Queue(expected) if expected else None,
        )
    except KeyError as missing:
        raise ValueError(f"Ticket {position} is missing the field {missing}") from missing
    except ValueError as error:
        raise ValueError(f"Ticket {position} ({entry.get('id', '?')}): {error}") from error
