# Ticket-Routing im Kundenservice mit Jev

Diese Demo ordnet 100 Kundenservice-Tickets vier Warteschlangen zu. Die
Zuordnung trifft Jev, das System-One-Modell von typesafe.ai. Jev liest den
Ticketext und beantwortet vier typisierte Fragen. Jede Antwort trägt eine
kalibrierte Wahrscheinlichkeit. Ein Aufruf je Ticket genügt.

Jedes Ticket trägt zusätzlich die Warteschlange, die ein Disponent wählt.
Daran misst der Lauf die Trefferquote. Jev trifft 89 von 97 Zuordnungen. Das
sind 92 Prozent. Sieben der acht Fehler bleiben unter der Konfidenzschwelle
von 0,80. Das Modell meldet sie damit selbst.

## Jev beantwortet vier Fragen je Ticket

| Frage        | Primitiv | Ergebnis                                                |
|--------------|----------|---------------------------------------------------------|
| `queue`      | `choice` | eine Warteschlange, dazu die Verteilung über alle vier   |
| `urgency`    | `score`  | Stufe von Routine bis Immediate, dazu die Konfidenz      |
| `mood`       | `score`  | Stufe von Factual bis Outraged, dazu die Konfidenz       |
| `escalation` | `noul`   | Wahrscheinlichkeit, dass die Teamleitung eingreift       |

`urgency` bewertet die Sachlage. `mood` bewertet allein die Sprache. Beide
Werte laufen auseinander. Die Kennzahl `tone_above_substance` zieht `urgency`
von `mood` ab. Ein Wert über null steht für einen scharfen Ton bei geringer
Sachlage. Ein Wert unter null steht für einen sachlichen Ton bei hoher Dringlichkeit.

## Die Konfidenz misst etwas anderes als die Wahrscheinlichkeit

Eine `choice`-Antwort liefert zwei Größen. Beide beantworten verschiedene
Fragen.

`probabilities` verteilt die Wahrscheinlichkeit auf alle Optionen. Die Summe
beträgt 1,0. Der Wert je Option gibt an, wie stark das Modell diese Option
stützt.

`confidence` gilt allein für die gewählte Option. Der Wert misst den Abstand
zum Zufall. Bei vier Optionen entspricht die Wahrscheinlichkeit 0,25 dem
reinen Raten. Diese Lage ergibt die Konfidenz 0. Die Wahrscheinlichkeit 1,00
ergibt die Konfidenz 1.

In allen geprüften Antworten gilt diese Umrechnung:

```
confidence = (p - 1/n) / (1 - 1/n)       n = Anzahl der Optionen
                                         p = Wahrscheinlichkeit der Wahl
```

| Optionen | p(Wahl) | Konfidenz |
|----------|---------|-----------|
| 4        | 0,25    | 0,00      |
| 4        | 0,50    | 0,33      |
| 4        | 0,75    | 0,67      |
| 2        | 0,50    | 0,00      |
| 2        | 0,75    | 0,50      |

Daraus folgt die Regel für die Praxis: Setze Schwellen auf `confidence`. Die
rohe Wahrscheinlichkeit hängt von der Anzahl der Optionen ab. Bei zwei
Optionen bedeutet 0,50 reines Raten. Bei zehn Optionen bedeutet derselbe Wert
eine deutliche Präferenz. Die Konfidenz gleicht diesen Unterschied aus.
`RoutingPolicy` nutzt deshalb `confidence`.

Den Umfang der Prüfung nennt [ERGEBNISSE.md](ERGEBNISSE.md).

## Die Demo startet mit vier Befehlen

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env        # TYPESAFE_API_KEY eintragen
.venv/bin/python -m routing.cli
```

Den Zugang zur Jev-API trägst du in `.env` ein. Die Datei bleibt über
`.gitignore` außerhalb der Versionsverwaltung. `.env.example` zeigt die Form.

Weitere Aufrufe:

```bash
.venv/bin/python -m routing.cli --limit 5              # nur die ersten fünf
.venv/bin/python -m routing.cli --ticket NT-2047       # ein einzelnes Ticket
.venv/bin/python -m routing.cli --min-confidence 0.95  # strenger prüfen
.venv/bin/python -m routing.cli --repeat 3             # Streuung messen
.venv/bin/python -m routing.cli --json > out/run.json  # Ergebnis als JSON
```

Wenn die API bei einem Ticket ausfällt, läuft der Stapel weiter. Das Ticket
erscheint in der Fehlerliste. Der Rückgabewert ist dann 1.

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

Der Lauf dauert 4,2 Sekunden. Er kostet 0,0041 USD bei 97.851 Eingabe-Token.
Die Tickets verteilen sich auf Technical 31, Billing 30, Sales 20 und
Contracts 19. Davon laufen 65 in der Regelbearbeitung. 15 gehen an die
Sichtprüfung, 13 in die Eilbearbeitung, 7 in die Eskalation.

Die Spalte `Hit` vergleicht die Wahl mit der Erwartung des Disponenten. Bei
einer Abweichung nennt sie die erwartete Warteschlange.

Die vollständigen Messungen stehen in [ERGEBNISSE.md](ERGEBNISSE.md).

## Die Tests laufen ohne Netzverbindung

```bash
.venv/bin/python -m pytest
```

Die 56 Tests ersetzen Jev durch eine Attrappe und eine aufgezeichnete Antwort.
Die Aufzeichnung liegt in `tests/recordings/`. Die Tests prüfen Domänenmodell,
Übersetzung, Richtlinie, Fehlerbehandlung, Ticketablage und Ausgabe. Der
Testlauf arbeitet allein mit lokalen Daten.

Die 100 Demo-Tickets stehen in `data/tickets.yaml`. Alle Namen, Nummern und
Beträge darin sind erfunden.

## Die Lizenz ist MIT

Der Code steht unter der MIT-Lizenz. Der Text steht in [LICENSE](LICENSE).

Die Demo nutzt die Jev-API von typesafe.ai. Für den Zugang gelten die
Bedingungen des Anbieters.
