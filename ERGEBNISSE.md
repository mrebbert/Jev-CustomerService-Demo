# Was die Jev-Läufe über die 100 Demo-Tickets zeigen

Alle Zahlen stammen aus Läufen vom 21. bis 25. September 2026 gegen
`jev-1.13.0`. Die Tickets stehen in `data/tickets.yaml`, den Lauf startet
`python -m routing.cli`. Als Referenz dient ein einzelner Lauf; der Abschnitt
zur Wiederholbarkeit zeigt, wie stark die Zahlen über mehrere Läufe wandern.

## Ein Lauf kostet vier Sekunden und einen halben Cent

| Kennzahl        | Wert                                        |
|-----------------|---------------------------------------------|
| Tickets         | 100                                         |
| Dauer           | 4,1 Sekunden, acht Tickets nebenläufig      |
| Eingabe-Token   | 95.851                                      |
| Kosten          | 0,0040 USD bei 0,042 USD je Million Token   |
| Modell          | jev-1.13.0                                  |

Ein Aufruf je Ticket beantwortet alle vier Fragen. Ausgabe-Token berechnet
typesafe.ai nicht, daher zählt allein der Ticketext plus die Fragen. Ein
Posteingang von 10.000 Tickets kostet nach dieser Messung 40 Cent.

## Die Last verteilt sich ungleich auf die vier Teams

| Warteschlange  | Tickets |
|----------------|---------|
| technik        | 32      |
| abrechnung     | 30      |
| vertragswesen  | 19      |
| vertrieb       | 19      |

| Nächster Schritt | Tickets |
|------------------|---------|
| Regelbearbeitung | 60      |
| Sichtprüfung     | 18      |
| Eilbearbeitung   | 14      |
| Eskalation       | 8       |

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

## Jedes fünfte Ticket trägt zwei Anliegen

20 Tickets bleiben unter 80 Prozent Konfidenz. Die mittlere Konfidenz über alle
100 liegt bei 0,887. Die unsichersten Fälle teilen ein Muster: Das Anliegen
gehört fachlich zu zwei Teams.

| Ticket  | Konfidenz | Gewählt       | Stärkste Alternative | Warum geteilt                                            |
|---------|-----------|---------------|----------------------|----------------------------------------------------------|
| NT-2081 | 10 %      | vertragswesen | technik 32 %         | Drohung mit der Verbraucherzentrale ohne klares Sachthema |
| NT-2127 | 33 %      | technik       | vertragswesen 38 %   | Verfügbarkeit prüfen vor einem Umzug                     |
| NT-2135 | 33 %      | vertrieb      | technik 49 %         | Netzabdeckung als Frage vor dem Vertragsabschluss        |
| NT-2128 | 34 %      | vertragswesen | technik 44 %         | Rufnummer unterdrücken: Stammdaten oder Einstellung      |
| NT-2111 | 37 %      | vertrieb      | technik 38 %         | Roamingsperre: Option buchen oder technisch sperren      |
| NT-2080 | 38 %      | abrechnung    | vertragswesen 46 %   | Kündigung nicht umgesetzt, Erstattung offen              |

Diese Fälle sind der eigentliche Nutzen der Demo. Ein Modell, das nur ein Team
nennt, schickt sie stillschweigend in die falsche Warteschlange. Ein Modell mit
kalibrierter Konfidenz meldet sie zur Sichtprüfung.

## Die Wahl wackelt genau dort, wo das Modell Unsicherheit meldet

Drei Läufe über dieselben 100 Tickets:

| Kennzahl        | Lauf 1 | Lauf 2 | Lauf 3 |
|-----------------|--------|--------|--------|
| technik         | 32     | 32     | 33     |
| abrechnung      | 30     | 30     | 30     |
| vertragswesen   | 19     | 19     | 18     |
| vertrieb        | 19     | 19     | 19     |
| Eskalation      | 8      | 8      | 8      |
| Eilbearbeitung  | 14     | 14     | 14     |
| Sichtprüfung    | 18     | 20     | 20     |

Vier Tickets wechseln über die drei Läufe die Warteschlange: NT-2081, NT-2127,
NT-2128 und NT-2135. Das sind genau vier der fünf Tickets mit der niedrigsten
Konfidenz. Alle 96 übrigen bleiben stabil.

Die Dringlichkeitswerte weichen zwischen zwei Läufen um höchstens 0,13 ab.
Sieben Tickets liegen nahe der Rundungsgrenze von 1,5 zwischen Bald und
Dringend; vier davon wechseln dadurch die benannte Stufe, ohne dass sich der
zugrunde liegende Wert nennenswert bewegt.

Wer feste Schwellen setzt, plant diesen Spielraum ein. Wer Zahlen aus einem
Lauf in einen Bericht schreibt, nennt den Lauf.

## Der Ton folgt der Sachlage nicht

| Tonlage      | Tickets |
|--------------|---------|
| Sachlich     | 74      |
| Angespannt   | 12      |
| Verärgert    | 10      |
| Aufgebracht  | 4       |

Neun Tickets melden eine ernste Lage in ruhigem Ton, drei schreiben scharf über
eine Kleinigkeit. Die Gegenüberstellung trägt die ganze Demo:

| Ticket  | Anliegen                                            | Dringlichkeit | Stimmung        |
|---------|-----------------------------------------------------|---------------|-----------------|
| NT-2101 | Netzausfall im Gewerbegebiet, Spedition steht still | Sofort 2,7    | Sachlich 0,1    |
| NT-2072 | Notrufweiterleitung für 42 Heimbewohner ausgefallen | Dringend 2,4  | Sachlich 0,0    |
| NT-2053 | Zahnarztpraxis ohne Telefon und Internet            | Sofort 3,0    | Angespannt 0,7  |
| NT-2071 | Rechnung kam einen Tag zu spät, in Großbuchstaben   | Bald 0,5      | Aufgebracht 2,6 |
| NT-2126 | Preiszusage nicht eingehalten, Vorwurf Betrug       | Bald 1,3      | Aufgebracht 3,0 |
| NT-2089 | Kritik an der Telefonhotline                        | Routine 0,4   | Verärgert 2,0   |

Wer nach Lautstärke sortiert, nimmt NT-2071 vor NT-2101. Die getrennten Skalen
drehen das um.

## Eskalation und Zuordnung sind unabhängig

Acht Tickets überschreiten 60 Prozent Eskalationswahrscheinlichkeit. Ihre
Konfidenz bei der Warteschlange reicht von 10 bis 100 Prozent:

| Ticket  | Eskalation | Warteschlange | Konfidenz |
|---------|------------|---------------|-----------|
| NT-2047 | 93 %       | abrechnung    | 100 %     |
| NT-2081 | 90 %       | vertragswesen | 10 %      |
| NT-2126 | 86 %       | abrechnung    | 77 %      |
| NT-2118 | 85 %       | abrechnung    | 100 %     |
| NT-2060 | 76 %       | vertragswesen | 96 %      |
| NT-2077 | 70 %       | abrechnung    | 86 %      |
| NT-2138 | 61 %       | technik       | 93 %      |
| NT-2085 | 60 %       | vertragswesen | 90 %      |

NT-2081 zeigt den Nutzen getrennter Fragen am deutlichsten: Das Team bleibt
offen, die Chefsache steht fest.

## Die Schwelle für die Sichtprüfung kostet Handarbeit

Ein Vergleich über dieselben Tickets, allein `--mindestkonfidenz` verschoben:

| Schwelle | Sichtprüfung | Anteil |
|----------|--------------|--------|
| 0,80     | 18 von 100   | 18 %   |
| 0,95     | 27 von 100   | 27 %   |

Die Zuordnung auf die Teams bleibt dabei gleich. Die Schwelle steuert allein,
wer nachsieht.

Über die ersten 50 Tickets lag die Quote bei 0,80 noch bei 10 Prozent. Die
zweite Hälfte der Sammlung enthält mehr Mischanliegen, etwa Verfügbarkeitsfragen
vor einem Vertragsabschluss. Genau daran zeigt sich, wovon die Quote abhängt:
nicht vom Modell, sondern vom Zuschnitt der Warteschlangen. Wer viele
Grenzfälle sieht, schneidet die Teams neu oder baut eine zweite Stufe ein.

## Der Score ist ein Erwartungswert, keine Stufennummer

Jev gibt bei einer `score`-Frage die Verteilung über alle Stufen zurück. Der
Wert `score` ist der damit gewichtete Mittelwert. Nachgerechnet:

| Ticket  | Verteilung über Routine, Bald, Dringend, Sofort | `score` | Summe(Stufe × p) |
|---------|--------------------------------------------------|---------|------------------|
| NT-2043 | 1,00 / 0 / 0 / 0                                 | 0,00    | 0,00             |
| NT-2041 | 0,01 / 0,51 / 0,48 / 0                           | 1,46    | 1,47             |
| NT-2046 | 0 / 0 / 0,56 / 0,44                              | 2,43    | 2,44             |
| NT-2053 | 0 / 0 / 0 / 1,00                                 | 3,00    | 3,00             |

Die Restabweichung von einem Hundertstel stammt aus der gerundeten Ausgabe der
Wahrscheinlichkeiten. Die Nachkommastelle trägt Information: NT-2041 steht bei
1,46 auf der Kippe zwischen Bald und Dringend, NT-2046 bei 2,43 sicher über der
Schwelle. Darum hält `Urgency` den Rohwert und rundet erst für die Anzeige.

## Zwei Beobachtungen für den Nachbau

**Die Skala kennt keine Freude.** NT-2073, NT-2086 und NT-2121 sind Lob und
landen bei Sachlich 0,0. Die Stufen messen allein die Schärfe. Wer
Dankesschreiben erkennen will, stellt dafür eine eigene `noul`-Frage.

**Aufgezeichnete Antworten liest man als JSON-Text.** Die Antwortmodelle des SDK
laufen mit `strict=True`, und die Stufenschlüssel einer Score-Antwort gelten als
Zahlen. `model_validate_json` rechnet die Zeichenketten des Formats selbst um,
der Umweg über `json.loads` und `model_validate` scheitert daran.
