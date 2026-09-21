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

Auslastung der Warteschlangen
  technik        18 Tickets
  abrechnung     13 Tickets
  vertragswesen  11 Tickets
  vertrieb        8 Tickets

Tonlage der Tickets
  Sachlich       35 Tickets
  Angespannt      7 Tickets
  Verärgert       6 Tickets
  Aufgebracht     2 Tickets

Ton über Sache:    2  (NT-2071, NT-2089)
Sache über Ton:    6  (NT-2046, NT-2051, NT-2053, NT-2061, NT-2064, NT-2072)

Eilbearbeitung:    12 von 50
Eskalation:        5 von 50
Sichtprüfung:      5 von 50
Modell:            jev-1.13.0
Eingabe-Token:     48165
Kosten:            0.0020 USD
```

Der ganze Lauf dauert rund zwei Sekunden, weil der Router acht Tickets
nebenläufig bewertet. Die Kosten liegen bei einem Fünftel Cent für 50 Tickets.

## Die Grenzfälle zeigen den Nutzen der Wahrscheinlichkeiten

**Der Ton täuscht über die Sachlage.** NT-2071 schreibt in Großbuchstaben über
eine Rechnung, die einen Tag zu spät kam: Aufgebracht 2.7 bei Dringlichkeit 0.5.
NT-2072 meldet nüchtern den Ausfall der Notrufweiterleitung für 42 Bewohner
eines Pflegeheims: Sachlich 0.0 bei Dringlichkeit 2.3. Wer nach Lautstärke
sortiert, bearbeitet das falsche Ticket zuerst.

**Eine unsichere Zuordnung meldet sich selbst.** NT-2081 droht mit der
Verbraucherzentrale wegen einer nicht gestrichenen Rechnungsposition. Die
Warteschlange bleibt mit 13 Prozent offen, denn das Anliegen trägt Abrechnung
und Vertragswesen zugleich. Die Eskalation steht dagegen bei 90 Prozent, also
greift sie und ein Mensch entscheidet über das Team.

**Der Ausnahmefall trägt beides.** NT-2077 verbindet eine Sperre mit einem
stillstehenden Onlineshop: Sofort 3.0, Aufgebracht 2.9, Eskalation 67 Prozent.
Hier decken sich Ton und Sachlage.

**Die Skala kennt keine Freude.** NT-2073 und NT-2086 sind Lob. Beide landen bei
Sachlich 0.0, denn die Stufen messen allein die Schärfe. Wer Dankesschreiben
erkennen will, stellt dafür eine eigene `noul`-Frage.

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
