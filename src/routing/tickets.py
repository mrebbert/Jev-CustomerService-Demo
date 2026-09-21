"""Lädt die Demo-Tickets aus der YAML-Ablage."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml

from routing.domain import Ticket

STANDARDABLAGE = Path(__file__).resolve().parents[2] / "data" / "tickets.yaml"


def lade_tickets(pfad: Path | str = STANDARDABLAGE) -> list[Ticket]:
    """Liest die Tickets und gibt sie in der Reihenfolge der Datei zurück."""
    rohdaten = yaml.safe_load(Path(pfad).read_text(encoding="utf-8"))
    return [
        Ticket(
            kennung=eintrag["kennung"],
            betreff=eintrag["betreff"],
            text=eintrag["text"].strip(),
            eingang=datetime.fromisoformat(eintrag["eingang"]),
            kanal=eintrag.get("kanal", "E-Mail"),
        )
        for eintrag in rohdaten["tickets"]
    ]
