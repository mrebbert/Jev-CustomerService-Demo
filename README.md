# Ticket-Routing im Kundenservice mit Jev

Diese Demo verteilt 100 eingehende Kundenservice-Tickets auf vier
Warteschlangen. Die Entscheidung trifft Jev, das System-One-Modell von
typesafe.ai: Es liest den Ticketext und beantwortet vier typisierte Fragen mit
kalibrierten Wahrscheinlichkeiten. Ein Aufruf je Ticket genügt.

Jedes Ticket trägt zusätzlich die Warteschlange, die ein erfahrener Disponent
wählt. Daran misst der Lauf, ob Jev richtig liegt: **89 von 97 Tickets
stimmen, das sind 92 Prozent.** Sieben der acht Fehler meldet das Modell selbst,
weil ihre Konfidenz unter der Schwelle bleibt.

## Jev beantwortet vier Fragen zugleich

| Frage       | Primitiv | Ergebnis                                                        |
|-------------|----------|-----------------------------------------------------------------|
| `queue`     | `choice` | eine der vier Warteschlangen, dazu die Verteilung über alle vier |
| `urgency`   | `score`  | Stufe zwischen Routine und Immediate, dazu die Konfidenz         |
| `mood`      | `score`  | Ton zwischen Factual und Outraged, dazu die Konfidenz            |
| `escalation`| `noul`   | Wahrscheinlichkeit, dass die Teamleitung eingreifen muss         |

Dringlichkeit und Stimmung messen verschiedene Dinge. Die eine Frage wiegt die
Sachlage, die andere allein die Sprache. Die Kennzahl `tone_above_substance`
zieht beide voneinander ab und zeigt, wo sie auseinanderlaufen.

## Der Schnitt folgt dem Bounded Context Ticket-Routing

```
src/routing/
  domain.py       Ticket, Queue, Urgency, Mood, RoutingDecision, RoutingPolicy
  jev_client.py   Anti-Corruption Layer: die einzige Stelle mit Jev-Begriffen
  router.py       Anwendungsfall, Port TicketClassifier, RoutingRun, Stabilität
  tickets.py      lädt die Demo-Tickets und prüft sie
  cli.py          Einstieg und Ausgabe
data/tickets.yaml 100 deutsche Demo-Tickets mit erwarteter Warteschlange
tests/            56 Tests gegen eine aufgezeichnete Jev-Antwort, ohne Netz
```

Der Code ist durchgängig englisch, die Ticketdaten sind deutsch. Die Kriterien,
nach denen Jev entscheidet, stammen aus dem Domänenmodell: `Queue.description`
liefert die Abgrenzung der Teams, `UrgencyLevel` und `MoodLevel` die Stufen.
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
.venv/bin/python -m routing.cli --limit 5              # nur die ersten fünf
.venv/bin/python -m routing.cli --ticket NT-2047       # ein einzelnes Ticket
.venv/bin/python -m routing.cli --min-confidence 0.95  # strenger prüfen
.venv/bin/python -m routing.cli --repeat 3             # Streuung sichtbar machen
.venv/bin/python -m routing.cli --json > out/run.json  # Ergebnis weiterverarbeiten
```

Ein Ticket, das die API nicht beantwortet, beendet den Lauf nicht. Es landet in
der Fehlerliste, der Rest des Stapels steht. Der Rückgabewert ist dann 1.

## Ein Lauf über alle 100 Tickets

```
┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Id      ┃ Subject                                ┃ Queue      ┃ Conf. ┃ Urgency        ┃ Mood                ┃  Esc. ┃ Step              ┃   Hit   ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ NT-2071 │ UNGLAUBLICH!!! Rechnung einen Tag zu … │ billing    │  100% │ Soon 0.5       │ Outraged 2.7 (67%)  │   25% │ Standard handling │   yes   │
│ NT-2081 │ Letzte Warnung vor der Verbraucherzen… │ technical  │   19% │ Soon 1.1       │ Annoyed 2.4 (35%)   │   90% │ Escalation        │ billing │
│ NT-2101 │ Netzausfall im Gewerbegebiet seit heu… │ technical  │  100% │ Immediate 2.8  │ Factual 0.1 (93%)   │    6% │ Rush handling     │   yes   │
│ NT-2126 │ DAS IST BETRUG                         │ billing    │   88% │ Soon 1.3       │ Outraged 3.0 (100%) │   87% │ Escalation        │   yes   │
└─────────┴────────────────────────────────────────┴────────────┴───────┴────────────────┴─────────────────────┴───────┴───────────────────┴─────────┘
```

Der Lauf dauert 4,2 Sekunden und kostet 0,0041 USD bei 97.851 Eingabe-Token.
Die Last verteilt sich auf Technical 31, Billing 30, Sales 20 und Contracts 19
Tickets; 65 laufen in der Regelbearbeitung, 15 gehen an die Sichtprüfung, 13 in
die Eilbearbeitung, 7 eskalieren.

Die vollständigen Messungen und was sie über Jev zeigen, stehen in
[ERGEBNISSE.md](ERGEBNISSE.md): die Trefferquote je Konfidenzschwelle, die
Grenzfälle mit geteiltem Anliegen, die Tonlage über alle 100 Tickets, der
Unterschied zwischen `confidence` und der Wahrscheinlichkeit der gewählten
Option und die Streuung über drei Läufe.

## Tests laufen ohne Netz

```bash
.venv/bin/python -m pytest
```

Die 56 Tests ersetzen Jev durch eine Attrappe und eine aufgezeichnete Antwort in
`tests/recordings/`. Sie prüfen Domänenmodell, Übersetzung, Richtlinie,
Fehlerbehandlung, Ticketablage und die Ausgabe der CLI, ohne einen Token zu
verbrauchen.

## Die Zugangsdaten bleiben außerhalb des Repos

`TYPESAFE_API_KEY` steht in `.env`, die Datei bleibt über `.gitignore` draußen.
`.env.example` zeigt nur die Form.
