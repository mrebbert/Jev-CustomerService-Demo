# Ticket-Routing im Kundenservice mit Jev

Diese Demo verteilt 50 eingehende Kundenservice-Tickets auf vier
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
data/tickets.yaml 50 deutsche Demo-Tickets, frei erfunden
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

## Ein Lauf über alle 50 Tickets

```
┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Kennung ┃ Betreff                                ┃ Warteschlange ┃ Konf. ┃ Dringlichkeit ┃ Stimmung              ┃ Eskal. ┃ Schritt          ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ NT-2071 │ UNGLAUBLICH!!! Rechnung einen Tag zu …  │ abrechnung    │  100% │ Routine 0.5   │ Aufgebracht 2.7 (67%) │    24% │ Regelbearbeitung │
│ NT-2072 │ Hinweis zum Ausfall der Notrufweiterl…  │ technik       │  100% │ Dringend 2.3  │ Sachlich 0.0 (100%)   │     6% │ Eilbearbeitung   │
│ NT-2077 │ SIE HABEN MEINEN ANSCHLUSS GESPERRT     │ abrechnung    │   87% │ Sofort 3.0    │ Aufgebracht 2.9 (91%) │    67% │ Eskalation       │
│ NT-2081 │ Letzte Warnung vor der Verbraucherzen…  │ vertragswesen │   13% │ Bald 1.2      │ Verärgert 2.4 (39%)   │    90% │ Eskalation       │
└─────────┴────────────────────────────────────────┴───────────────┴───────┴───────────────┴───────────────────────┴────────┴──────────────────┘
```

Der Lauf dauert 2,4 Sekunden und kostet 0,0020 USD bei 48.165 Eingabe-Token.
Die Last verteilt sich auf Technik 18, Abrechnung 13, Vertragswesen 11 und
Vertrieb 8 Tickets; 12 gehen in die Eilbearbeitung, 5 eskalieren, 5 landen in
der Sichtprüfung.

Die vollständigen Messungen und was sie über Jev zeigen, stehen in
[ERGEBNISSE.md](ERGEBNISSE.md): die Tonlage über alle 50 Tickets, die
Grenzfälle mit niedriger Konfidenz, der Vergleich beider Konfidenzschwellen
und der Nachweis, dass ein `score` der Erwartungswert über die Stufen ist.

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
