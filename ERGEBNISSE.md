# Was die Jev-Läufe über die 100 Demo-Tickets zeigen

Alle Zahlen stammen aus Läufen vom 21. September 2026 gegen `jev-1.13.0`.
Die Tickets stehen in `data/tickets.yaml`, den Lauf startet
`python -m routing.cli`. Als Referenz dient ein einzelner Lauf; der Abschnitt
zur Streuung zeigt, wie stark die Zahlen über mehrere Läufe wandern.

## Jev trifft 92 Prozent der Zuordnungen

Jedes Ticket trägt im Feld `expected` die Warteschlange, die ein erfahrener
Disponent wählt. Dieses Feld erreicht das Modell nie; es dient allein der
Bewertung. Drei Tickets ohne Fachthema (NT-2074, NT-2121, NT-2124) tragen keine
Erwartung und bleiben außen vor.

| Kennzahl                  | Wert         |
|---------------------------|--------------|
| bewertete Tickets         | 97           |
| Treffer                   | 89 (91,8 %)  |
| Fehler                    | 8            |
| Median-Konfidenz Treffer  | 1,00         |
| Median-Konfidenz Fehler   | 0,62         |

Die beiden Mediane tragen die ganze Aussage: Wo Jev richtig liegt, ist es sich
sicher. Wo es falsch liegt, sagt es das.

## Die Konfidenz taugt als Filter

Dieselben 97 Tickets, allein `--min-confidence` verschoben:

| Schwelle | automatisch | davon falsch | Genauigkeit | Sichtprüfung |
|----------|-------------|--------------|-------------|--------------|
| 0,80     | 76          | 1            | 98,7 %      | 13           |
| 0,90     | 70          | 0            | 100 %       | 19           |
| 0,95     | 65          | 0            | 100 %       | 24           |

Bei 0,80 rutscht ein einziger Fehler durch: NT-2112 nennt einen falschen Namen
auf der Rechnung, Jev wählt mit 86 Prozent Billing statt Contracts. Fachlich
gehört die Korrektur zu den Stammdaten, die Nähe zur Rechnung liegt auf der
Hand.

Ab 0,90 arbeitet die Automatik fehlerfrei. Der Preis sind sechs zusätzliche
Sichtprüfungen, also 19 statt 13 von 97 Tickets. Wer keinen Fehler in der
Automatik zulässt, zahlt hier 6 Prozent mehr Handarbeit.

## Die acht Fehler liegen dort, wo zwei Teams zuständig sind

| Ticket  | Jev        | Erwartet  | Konfidenz | Warum geteilt                                           |
|---------|------------|-----------|-----------|---------------------------------------------------------|
| NT-2081 | contracts  | billing   | 14 %      | Drohung mit der Verbraucherzentrale wegen einer Rechnungsposition |
| NT-2080 | billing    | contracts | 34 %      | Kündigung nicht umgesetzt, Erstattung offen             |
| NT-2093 | billing    | technical | 55 %      | Technikertermine geplatzt, Verdienstausfall gefordert   |
| NT-2095 | contracts  | sales     | 56 %      | Studentenrabatt über die Laufzeit                       |
| NT-2127 | sales      | contracts | 66 %      | Verfügbarkeit prüfen vor einem Umzug                    |
| NT-2090 | technical  | sales     | 74 %      | Anschluss für einen Neubau, Termin gesucht              |
| NT-2122 | contracts  | technical | 78 %      | Gerät nach Vertragsende abholen                         |
| NT-2112 | billing    | contracts | 86 %      | Falscher Name auf der Rechnung                          |

Bei jedem dieser Tickets lässt sich die Erwartung bestreiten. Genau darum ist
die niedrige Konfidenz die richtige Antwort: Nicht das Modell irrt, der
Zuschnitt der Warteschlangen ist an dieser Stelle nicht trennscharf.

## Ein Lauf kostet vier Sekunden und einen halben Cent

| Kennzahl        | Wert                                        |
|-----------------|---------------------------------------------|
| Tickets         | 100                                         |
| Dauer           | 4,2 Sekunden, acht Tickets nebenläufig      |
| Eingabe-Token   | 97.851                                      |
| Kosten          | 0,0041 USD bei 0,042 USD je Million Token   |
| Modell          | jev-1.13.0                                  |

Ein Aufruf je Ticket beantwortet alle vier Fragen. Ausgabe-Token berechnet
typesafe.ai nicht, daher zählt allein der Ticketext plus die Fragen. Ein
Posteingang von 10.000 Tickets kostet nach dieser Messung 41 Cent.

## Die Last verteilt sich ungleich auf die vier Teams

| Warteschlange | Tickets |
|---------------|---------|
| technical     | 31      |
| billing       | 30      |
| sales         | 20      |
| contracts     | 19      |

| Nächster Schritt   | Tickets |
|--------------------|---------|
| Standard handling  | 65      |
| Review desk        | 15      |
| Rush handling      | 13      |
| Escalation         | 7       |

Jedes Ticket nimmt genau einen Weg. Die Eskalation geht der Sichtprüfung vor,
die Sichtprüfung der Eilbearbeitung.

## Die Konfidenz ist ein eigenes Maß, nicht die Wahrscheinlichkeit der Wahl

Eine `choice`-Antwort liefert beides: `probabilities` über alle Optionen und
`confidence` für die getroffene Wahl. Beide fallen auseinander.

| Beobachtung                                         | Tickets |
|-----------------------------------------------------|---------|
| `confidence` gleich der Wahrscheinlichkeit der Wahl | 56      |
| `confidence` niedriger                              | 44      |
| `confidence` höher                                  | 0       |

Die gewählte Option ist in allen 100 Fällen die wahrscheinlichste. Die
Konfidenz fällt aber, sobald die zweite Option nahe heranrückt:

| Ticket  | p(Wahl) | p(zweite) | Abstand | `confidence` |
|---------|---------|-----------|---------|--------------|
| NT-2081 | 0,32    | 0,32      | 0,00    | 0,10         |
| NT-2135 | 0,50    | 0,49      | 0,01    | 0,33         |
| NT-2127 | 0,50    | 0,38      | 0,12    | 0,33         |
| NT-2111 | 0,52    | 0,38      | 0,14    | 0,37         |

Für eine Schwelle taugt daher `confidence`, nicht die Einzelwahrscheinlichkeit.
Die Richtlinie in `RoutingPolicy` nutzt genau diesen Wert.

## Die Wahl wackelt genau dort, wo das Modell Unsicherheit meldet

`--repeat 3` bewertet jedes Ticket dreimal und vergleicht die Zuordnungen:

```
Stability over 3 runs
  same queue every time  99 of 100
    NT-2081  technical×2, contracts×1
```

99 von 100 Tickets landen jedes Mal im selben Team. Das einzige wandernde ist
NT-2081, also das Ticket mit der niedrigsten Konfidenz im ganzen Stapel. Die
Dringlichkeitswerte weichen zwischen zwei Läufen um höchstens 0,13 ab.

Wer feste Schwellen setzt, plant diesen Spielraum ein. Wer Zahlen aus einem
Lauf in einen Bericht schreibt, nennt den Lauf.

## Der Ton folgt der Sachlage nicht

| Tonlage  | Tickets |
|----------|---------|
| Factual  | 74      |
| Tense    | 12      |
| Annoyed  | 10      |
| Outraged | 4       |

Neun Tickets melden eine ernste Lage in ruhigem Ton, drei schreiben scharf über
eine Kleinigkeit:

| Ticket  | Anliegen                                            | Dringlichkeit | Stimmung     |
|---------|-----------------------------------------------------|---------------|--------------|
| NT-2101 | Netzausfall im Gewerbegebiet, Spedition steht still | Immediate 2,8 | Factual 0,1  |
| NT-2072 | Notrufweiterleitung für 42 Heimbewohner ausgefallen | Urgent 2,4    | Factual 0,0  |
| NT-2053 | Zahnarztpraxis ohne Telefon und Internet            | Immediate 3,0 | Tense 0,7    |
| NT-2071 | Rechnung kam einen Tag zu spät, in Großbuchstaben   | Soon 0,5      | Outraged 2,7 |
| NT-2126 | Preiszusage nicht eingehalten, Vorwurf Betrug       | Soon 1,3      | Outraged 3,0 |
| NT-2089 | Kritik an der Telefonhotline                        | Routine 0,4   | Annoyed 2,0  |

Wer nach Lautstärke sortiert, nimmt NT-2071 vor NT-2101. Die getrennten Skalen
drehen das um.

## Eskalation und Zuordnung sind unabhängig

Sieben bis acht Tickets überschreiten 60 Prozent Eskalationswahrscheinlichkeit.
Ihre Konfidenz bei der Warteschlange reicht von 14 bis 100 Prozent:

| Ticket  | Eskalation | Warteschlange | Konfidenz |
|---------|------------|---------------|-----------|
| NT-2047 | 93 %       | billing       | 100 %     |
| NT-2081 | 90 %       | contracts     | 14 %      |
| NT-2126 | 87 %       | billing       | 88 %      |
| NT-2118 | 85 %       | billing       | 100 %     |
| NT-2060 | 76 %       | contracts     | 96 %      |
| NT-2077 | 70 %       | billing       | 86 %      |
| NT-2138 | 61 %       | technical     | 93 %      |

NT-2081 zeigt den Nutzen getrennter Fragen am deutlichsten: Das Team bleibt
offen, die Chefsache steht fest.

## Der Score ist ein Erwartungswert, keine Stufennummer

Jev gibt bei einer `score`-Frage die Verteilung über alle Stufen zurück. Der
Wert `score` ist der damit gewichtete Mittelwert. Nachgerechnet:

| Ticket  | Verteilung über Routine, Soon, Urgent, Immediate | `score` | Summe(Stufe × p) |
|---------|--------------------------------------------------|---------|------------------|
| NT-2043 | 1,00 / 0 / 0 / 0                                 | 0,00    | 0,00             |
| NT-2041 | 0,01 / 0,51 / 0,48 / 0                           | 1,46    | 1,47             |
| NT-2046 | 0 / 0 / 0,56 / 0,44                              | 2,43    | 2,44             |
| NT-2053 | 0 / 0 / 0 / 1,00                                 | 3,00    | 3,00             |

Die Restabweichung von einem Hundertstel stammt aus der gerundeten Ausgabe der
Wahrscheinlichkeiten. Die Nachkommastelle trägt Information: NT-2041 steht bei
1,46 auf der Kippe zwischen Soon und Urgent, NT-2046 bei 2,43 sicher über der
Schwelle. Darum hält `Urgency` den Rohwert und rundet erst für die Anzeige.

## Zwei Beobachtungen für den Nachbau

**Die Skala kennt keine Freude.** NT-2073, NT-2086 und NT-2121 sind Lob und
landen bei Factual 0,0. Die Stufen messen allein die Schärfe. Wer
Dankesschreiben erkennen will, stellt dafür eine eigene `noul`-Frage.

**Aufgezeichnete Antworten liest man als JSON-Text.** Die Antwortmodelle des SDK
laufen mit `strict=True`, und die Stufenschlüssel einer Score-Antwort gelten als
Zahlen. `model_validate_json` rechnet die Zeichenketten des Formats selbst um,
der Umweg über `json.loads` und `model_validate` scheitert daran.
