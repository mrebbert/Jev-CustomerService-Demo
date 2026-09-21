# Ticket-Routing im Kundenservice mit Jev

Diese Demo verteilt eingehende Kundenservice-Tickets auf vier Warteschlangen.
Die Entscheidung trifft Jev, das System-One-Modell von typesafe.ai: Es liest den
Ticketext und beantwortet drei typisierte Fragen mit kalibrierten
Wahrscheinlichkeiten. Ein Aufruf je Ticket genügt.

## Jev beantwortet drei Fragen zugleich

| Frage            | Primitiv | Ergebnis                                                        |
|------------------|----------|-----------------------------------------------------------------|
| `queue`          | `choice` | eine der vier Warteschlangen, dazu die Verteilung über alle vier |
| `dringlichkeit`  | `score`  | Stufe zwischen Routine und Sofort, dazu die Konfidenz            |
| `eskalation`     | `noul`   | Wahrscheinlichkeit, dass die Teamleitung eingreifen muss         |

Die Wahrscheinlichkeiten tragen die Fachlogik: Ab 80 Prozent Konfidenz läuft die
Zuordnung durch, darunter sieht ein Mensch nach. Ab 60 Prozent
Eskalationswahrscheinlichkeit geht das Ticket an die Teamleitung. Beide Schwellen
lassen sich beim Aufruf verschieben.

## Der Schnitt folgt dem Bounded Context Ticket-Routing

```
src/routing/
  domain.py       Ticket, Queue, Urgency, RoutingDecision, RoutingPolicy
  jev_client.py   Anti-Corruption Layer: die einzige Stelle mit Jev-Begriffen
  router.py       Anwendungsfall, Port TicketClassifier, nebenläufige Bewertung
  tickets.py      lädt die Demo-Tickets
  cli.py          Einstieg und Ausgabe
data/tickets.yaml 30 deutsche Demo-Tickets, frei erfunden
tests/            Tests gegen eine aufgezeichnete Jev-Antwort, ohne Netz
```

Die Kriterien, nach denen Jev entscheidet, stammen aus dem Domänenmodell:
`Queue.beschreibung` liefert die Abgrenzung der Teams, `UrgencyLevel` die Stufen.
Damit beschreibt die Fachsprache das Modell, nicht umgekehrt.

## So startest du die Demo

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env        # TYPESAFE_API_KEY eintragen
.venv/bin/python -m routing.cli
```

Weitere Aufrufe:

```bash
.venv/bin/python -m routing.cli --anzahl 5            # nur die ersten fünf
.venv/bin/python -m routing.cli --ticket NT-2047      # ein einzelnes Ticket
.venv/bin/python -m routing.cli --mindestkonfidenz 0.95   # strenger prüfen
.venv/bin/python -m routing.cli --json > out/lauf.json    # Ergebnis weiterverarbeiten
```

## Ein Lauf über alle 30 Tickets

```
┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Kennung ┃ Betreff                             ┃ Warteschlange ┃ Konf. ┃ Dringlichkeit  ┃ Eskal. ┃ Nächster Schritt          ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ NT-2042 │ Internet seit gestern Abend tot     │ technik       │  100% │ Dringend (2.0) │     5% │ Eilbearbeitung in technik │
│ NT-2047 │ Anwalt eingeschaltet wegen Nichtbe… │ abrechnung    │  100% │ Dringend (1.9) │    93% │ Eskalation an die Teamlei…│
│ NT-2053 │ Geschäftsanschluss ausgefallen, Pr… │ technik       │  100% │ Sofort (3.0)   │     7% │ Eilbearbeitung in technik │
│ NT-2068 │ Neuer Anschluss für Ferienwohnung   │ vertrieb      │   78% │ Routine (0.4)  │     3% │ Sichtprüfung in der Leit… │
└─────────┴─────────────────────────────────────┴───────────────┴───────┴────────────────┴────────┴───────────────────────────┘

Auslastung der Warteschlangen
  technik         9 Tickets
  vertragswesen   8 Tickets
  abrechnung      7 Tickets
  vertrieb        6 Tickets

Eilbearbeitung:    9 von 30
Eskalation:        2 von 30
Sichtprüfung:      1 von 30
Modell:            jev-1.13.0
Eingabe-Token:     24522
Kosten:            0.0010 USD
```

Der ganze Lauf dauert rund zwei Sekunden, weil der Router acht Tickets
nebenläufig bewertet. Die Kosten liegen bei einem Zehntel Cent für 30 Tickets.

## Die Grenzfälle zeigen den Nutzen der Wahrscheinlichkeiten

- **NT-2047** trägt eine Anwaltsdrohung. Die Warteschlange bleibt Abrechnung,
  die Eskalationswahrscheinlichkeit springt auf 93 Prozent.
- **NT-2060** kündigt wegen einer Dauerstörung. Jev wählt Vertragswesen und
  meldet zugleich 75 Prozent Eskalation.
- **NT-2068** fragt nach einem Anschluss für eine Ferienwohnung, halb Vertrieb
  und halb Technik. Mit 78 Prozent Konfidenz landet das Ticket in der
  Sichtprüfung statt in der falschen Warteschlange.

## Tests laufen ohne Netz

```bash
.venv/bin/python -m pytest
```

Die Tests ersetzen Jev durch eine Attrappe und eine aufgezeichnete Antwort in
`tests/aufzeichnungen/`. Damit prüfen sie Domänenmodell, Übersetzung und
Richtlinie, ohne einen Token zu verbrauchen.

## Die Zugangsdaten bleiben außerhalb des Repos

`TYPESAFE_API_KEY` steht in `.env`, die Datei bleibt über `.gitignore` draußen.
`.env.example` zeigt nur die Form.
