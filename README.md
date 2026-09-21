# Ticket-Routing im Kundenservice mit Jev

Diese Demo verteilt 100 eingehende Kundenservice-Tickets auf vier
Warteschlangen. Die Entscheidung trifft Jev, das System-One-Modell von
typesafe.ai: Es liest den Ticketext und beantwortet vier typisierte Fragen mit
kalibrierten Wahrscheinlichkeiten. Ein Aufruf je Ticket genügt.

## Jev beantwortet vier Fragen zugleich

| Frage            | Primitiv | Ergebnis                                                        |
|------------------|----------|-----------------------------------------------------------------|
| `queue`          | `choice` | eine der vier Warteschlangen, dazu die Verteilung über alle vier |
| `dringlichkeit`  | `score`  | Stufe zwischen Routine und Sofort, dazu die Konfidenz            |
| `stimmung`       | `score`  | Ton zwischen Sachlich und Aufgebracht, dazu die Konfidenz        |
| `eskalation`     | `noul`   | Wahrscheinlichkeit, dass die Teamleitung eingreifen muss         |

Dringlichkeit und Stimmung messen verschiedene Dinge. Die eine Frage wiegt die
Sachlage, die andere allein die Sprache. Die Kennzahl `ton_ueber_sache` zieht
beide voneinander ab und zeigt, wo sie auseinanderlaufen.

Die Wahrscheinlichkeiten tragen die Fachlogik: Ab 80 Prozent Konfidenz läuft die
Zuordnung durch, darunter sieht ein Mensch nach. Ab 60 Prozent
Eskalationswahrscheinlichkeit geht das Ticket an die Teamleitung. Beide Schwellen
lassen sich beim Aufruf verschieben.

## Der Schnitt folgt dem Bounded Context Ticket-Routing

```
src/routing/
  domain.py       Ticket, Queue, Urgency, Mood, RoutingDecision, RoutingPolicy
  jev_client.py   Anti-Corruption Layer: die einzige Stelle mit Jev-Begriffen
  router.py       Anwendungsfall, Port TicketClassifier, nebenläufige Bewertung
  tickets.py      lädt die Demo-Tickets
  cli.py          Einstieg und Ausgabe
data/tickets.yaml 100 deutsche Demo-Tickets, frei erfunden
tests/            Tests gegen eine aufgezeichnete Jev-Antwort, ohne Netz
```

Die Kriterien, nach denen Jev entscheidet, stammen aus dem Domänenmodell:
`Queue.beschreibung` liefert die Abgrenzung der Teams, `UrgencyLevel` und
`MoodLevel` liefern die Stufen.
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

## Ein Lauf über alle 100 Tickets

```
┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Kennung ┃ Betreff                                ┃ Warteschlange ┃ Konf. ┃ Dringlichkeit ┃ Stimmung               ┃ Eskal. ┃ Schritt          ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ NT-2071 │ UNGLAUBLICH!!! Rechnung einen Tag zu … │ abrechnung    │  100% │ Bald 0.5      │ Aufgebracht 2.6 (59%)  │    24% │ Regelbearbeitung │
│ NT-2081 │ Letzte Warnung vor der Verbraucherzen… │ vertragswesen │   10% │ Bald 1.1      │ Verärgert 2.4 (38%)    │    90% │ Eskalation       │
│ NT-2101 │ Netzausfall im Gewerbegebiet seit heu… │ technik       │  100% │ Sofort 2.7    │ Sachlich 0.1 (94%)     │     6% │ Eilbearbeitung   │
│ NT-2126 │ DAS IST BETRUG                         │ abrechnung    │   80% │ Bald 1.3      │ Aufgebracht 3.0 (100%) │    86% │ Eskalation       │
└─────────┴────────────────────────────────────────┴───────────────┴───────┴───────────────┴────────────────────────┴────────┴──────────────────┘
```

Der Lauf dauert 4,1 Sekunden und kostet 0,0040 USD bei 95.851 Eingabe-Token.
Die Last verteilt sich auf Technik 32, Abrechnung 30, Vertragswesen 19 und
Vertrieb 19 Tickets; 60 laufen in der Regelbearbeitung, 18 gehen in die
Sichtprüfung, 14 in die Eilbearbeitung, 8 eskalieren.

Die vollständigen Messungen und was sie über Jev zeigen, stehen in
[ERGEBNISSE.md](ERGEBNISSE.md): die Tonlage über alle 100 Tickets, die 20
Grenzfälle mit geteiltem Anliegen, der Vergleich beider Konfidenzschwellen,
der Unterschied zwischen `confidence` und der Wahrscheinlichkeit der gewählten
Option und der Nachweis, dass über drei Läufe genau die vier unsichersten
Tickets die Warteschlange wechseln.

## Tests laufen ohne Netz

```bash
.venv/bin/python -m pytest
```

Die 29 Tests ersetzen Jev durch eine Attrappe und eine aufgezeichnete Antwort in
`tests/aufzeichnungen/`. Damit prüfen sie Domänenmodell, Übersetzung und
Richtlinie, ohne einen Token zu verbrauchen.

## Die Zugangsdaten bleiben außerhalb des Repos

`TYPESAFE_API_KEY` steht in `.env`, die Datei bleibt über `.gitignore` draußen.
`.env.example` zeigt nur die Form.
