# Ticket-Routing im Kundenservice mit Jev

Diese Demo ordnet 100 Kundenservice-Tickets vier Warteschlangen zu. Die
Zuordnung trifft Jev, das System-One-Modell von typesafe.ai. Jev liest den
Ticket-Text und beantwortet vier Fragen mit festem Antworttyp. Jede Antwort
trägt eine Wahrscheinlichkeit. Ein Aufruf je Ticket genügt.

Jedes Ticket trägt zusätzlich die Warteschlange, die ein Disponent wählt.
Daran misst der Lauf die Trefferquote. Jev trifft 89 von 97 Zuordnungen. Das
sind 92 Prozent. Sieben der acht Fehler bleiben unter der Konfidenzschwelle
von 0,80. Das Modell meldet diese sieben Fehler damit selbst.

## Jev beantwortet vier Fragen je Ticket

| Frage        | Antworttyp | Ergebnis                                                |
|--------------|------------|-------------------------------------------------------|
| `queue`      | `choice` | eine Warteschlange, dazu die Verteilung über alle vier   |
| `urgency`    | `score`  | Stufe von Routine bis Immediate, dazu die Konfidenz      |
| `mood`       | `score`  | Stufe von Factual bis Outraged, dazu die Konfidenz       |
| `escalation` | `noul`   | Wahrscheinlichkeit, dass die Teamleitung eingreift       |

`urgency` bewertet die Sachlage. `mood` bewertet allein die Sprache. Beide
Werte laufen auseinander. Die Kennzahl `tone_above_substance` ist `mood` minus
`urgency`. Ein Wert über null steht für einen scharfen Ton bei geringer
Dringlichkeit. Ein Wert unter null steht für einen sachlichen Ton bei hoher
Dringlichkeit.

## Die Konfidenz zählt allein den Vorsprung vor dem Raten

Eine `choice`-Antwort liefert zwei Größen. Beide beantworten verschiedene
Fragen.

`probabilities` verteilt 100 Prozent auf alle Optionen. Der Wert je Option
gibt an, wie stark das Modell diese Option stützt.

`confidence` gilt allein für die gewählte Option. Der Wert zählt den Vorsprung
vor dem reinen Raten.

Ein Beispiel mit vier Warteschlangen: Wer rät, trifft mit 25 Prozent. Eine
Antwort mit 50 Prozent liegt damit 25 Prozentpunkte über dem Raten. Der
größtmögliche Vorsprung beträgt 75 Prozentpunkte, nämlich von 25 auf
100 Prozent. 25 geteilt durch 75 ergibt die Konfidenz 0,33.

Als Formel:

```
confidence = (p - 1/n) / (1 - 1/n)       n = Anzahl der Optionen
                                         p = Prozentsatz der gewählten Option
```

| Optionen | Raten trifft mit | Wahl trägt | Konfidenz |
|----------|------------------|------------|-----------|
| 4        | 25 %             | 25 %       | 0,00      |
| 4        | 25 %             | 50 %       | 0,33      |
| 4        | 25 %             | 75 %       | 0,67      |
| 2        | 50 %             | 50 %       | 0,00      |
| 2        | 50 %             | 75 %       | 0,50      |

Daraus folgt die Regel für die Praxis: Setze Schwellen auf `confidence`. Der
Prozentsatz allein hängt von der Anzahl der Optionen ab. Bei zwei Optionen
steht 50 Prozent für reines Raten, die Konfidenz beträgt 0. Bei zehn Optionen
steht derselbe Prozentsatz für eine deutliche Wahl, die Konfidenz beträgt
0,44. `RoutingPolicy` nutzt deshalb `confidence`.

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

Wenn die API bei einem Ticket ausfällt, laufen die übrigen Tickets weiter. Das
Ticket erscheint in der Fehlerliste. Der Rückgabewert ist dann 1.

## Ein Lauf über alle 100 Tickets dauert 4,2 Sekunden

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

Die Tabelle zeigt vier Zeilen aus einem Lauf. NT-2081 trägt die niedrigste
Konfidenz aller Tickets. Sein Wert wandert zwischen den Läufen.

Der Lauf kostet 0,0041 USD bei 97.851 Eingabe-Token. Die Tickets verteilen
sich auf Technical 31, Billing 30, Sales 20 und
Contracts 19. Davon laufen 65 im Standard handling. 14 gehen an die Review
desk, 13 in das Rush handling, 8 in die Escalation. Die Spalte `Step` nennt
diese vier Bearbeitungsarten.

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
