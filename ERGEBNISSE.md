# Messergebnisse der Jev-Läufe über 100 Demo-Tickets

## Die Messung beruht auf Läufen vom 21. September 2026

Alle Zahlen stammen aus Läufen vom 21. September 2026 gegen das Modell
`jev-1.13.0`. Die Tickets stehen in `data/tickets.yaml`. Den Lauf startet
`python -m routing.cli`. Als Referenz dient ein einzelner Lauf. Der Abschnitt
zur Streuung nennt die Abweichungen über mehrere Läufe.

Die Ausgabe benennt vier Bearbeitungsarten. Jedes Ticket erhält genau eine.

| Bearbeitungsart   | Bedeutung                                              |
|-------------------|--------------------------------------------------------|
| Standard handling | Die Warteschlange bearbeitet das Ticket im Regelfall.   |
| Rush handling     | Die Warteschlange bearbeitet das Ticket vorrangig.      |
| Review desk       | Ein Mitarbeiter prüft die Zuordnung vor der Weitergabe. |
| Escalation        | Die Teamleitung übernimmt das Ticket.                   |

Bei mehreren zutreffenden Merkmalen gilt diese Reihenfolge: Escalation vor
Review desk, Review desk vor Rush handling.

## Jev trifft 92 Prozent der Zuordnungen

Jedes Ticket trägt im Feld `expected` die Warteschlange, die ein Disponent
wählt. Der Lauf übergibt dem Modell allein Betreff und Text. Das Feld
`expected` dient allein der Bewertung. Drei Tickets mit unklarem Fachthema bleiben außerhalb der Wertung:
NT-2074, NT-2121 und NT-2124.

| Kennzahl                 | Wert        |
|--------------------------|-------------|
| bewertete Tickets        | 97          |
| Treffer                  | 89 (91,8 %) |
| Fehler                   | 8           |
| Median-Konfidenz Treffer | 1,00        |
| Median-Konfidenz Fehler  | 0,62        |

Der Median ist der mittlere Wert einer Reihe. Mehr als die Hälfte der Treffer
trägt die Konfidenz 1,00. Mehr als die Hälfte der Fehler bleibt unter 0,62.
Bei richtigen Zuordnungen meldet Jev also hohe Konfidenz, bei falschen
niedrige.

## Die Konfidenz trennt Treffer und Fehler

Die folgende Messung nutzt dieselben 97 Tickets. Allein der Wert von
`--min-confidence` ändert sich.

| Schwelle | automatisch | davon falsch | Genauigkeit | Review desk |
|----------|-------------|--------------|-------------|-------------|
| 0,80     | 76          | 1            | 98,7 %      | 13          |
| 0,90     | 70          | 0            | 100 %       | 19          |
| 0,95     | 65          | 0            | 100 %       | 24          |

Bei Schwelle 0,80 bleibt ein Fehler unerkannt. NT-2112 meldet einen falschen
Namen auf der Rechnung. Jev wählt mit 86 Prozent Konfidenz Billing. Der
Disponent erwartet Contracts, weil die Korrektur die Stammdaten betrifft.

Ab Schwelle 0,90 arbeitet die Automatik fehlerfrei. Dafür steigt die Zahl der
Prüfungen um sechs, von 13 auf 19 Tickets.

## Die acht Fehler betreffen Tickets mit zwei zuständigen Warteschlangen

| Ticket  | Jev       | Erwartet  | Konfidenz | Anliegen                                        |
|---------|-----------|-----------|-----------|--------------------------------------------------|
| NT-2081 | contracts | billing   | 14 %      | Drohung mit der Verbraucherzentrale wegen einer Rechnungsposition |
| NT-2080 | billing   | contracts | 34 %      | Kündigung nicht umgesetzt, Erstattung offen      |
| NT-2093 | billing   | technical | 55 %      | Technikertermine geplatzt, Verdienstausfall gefordert |
| NT-2095 | contracts | sales     | 56 %      | Studentenrabatt über die Laufzeit                |
| NT-2127 | sales     | contracts | 66 %      | Verfügbarkeit prüfen vor einem Umzug             |
| NT-2090 | technical | sales     | 74 %      | Anschluss für einen Neubau, Termin gesucht       |
| NT-2122 | contracts | technical | 78 %      | Gerät nach Vertragsende abholen                  |
| NT-2112 | billing   | contracts | 86 %      | Falscher Name auf der Rechnung                   |

Jedes dieser Tickets betrifft zwei Warteschlangen zugleich. Die Erwartung des
Disponenten bleibt in allen acht Fällen strittig. Die niedrige Konfidenz
beschreibt diesen Zustand zutreffend. Die Abgrenzung der vier Warteschlangen
deckt diese Anliegen doppelt ab.

## Die Konfidenz zählt allein den Vorsprung vor dem Raten

Eine `choice`-Antwort liefert zwei Größen mit verschiedener Bedeutung.

`probabilities` verteilt 100 Prozent auf alle Optionen. Der Wert je Option
gibt an, wie stark das Modell diese Option stützt.

`confidence` gilt allein für die gewählte Option. Der Wert zählt den
Vorsprung vor dem reinen Raten.

Ein Beispiel mit vier Warteschlangen: Wer rät, trifft mit 25 Prozent. NT-2135
erhält 50 Prozent auf Sales. Davon entfallen 25 Prozentpunkte auf das Raten.
Es bleiben 25 Prozentpunkte Vorsprung. Der größtmögliche Vorsprung beträgt
75 Prozentpunkte, nämlich von 25 auf 100 Prozent. 25 geteilt durch 75 ergibt
0,33. Genau diesen Wert meldet Jev als Konfidenz.

Als Formel:

```
confidence = (p - 1/n) / (1 - 1/n)       n = Anzahl der Optionen
                                         p = Prozentsatz der gewählten Option
```

Umfang der Prüfung: 100 Antworten mit vier Optionen aus vier Läufen, dazu je
eine Antwort mit zwei, drei und sechs Optionen. Die mittlere Abweichung
beträgt 0,0026. Die größte Abweichung beträgt 0,0100. Sie entspricht der
Rundung auf zwei Nachkommastellen in der Ausgabe.

| Ticket  | Optionen | p(Wahl) | Raten | Konfidenz | Formel |
|---------|----------|---------|-------|-----------|--------|
| NT-2081 | 4        | 0,32    | 0,25  | 0,10      | 0,093  |
| NT-2135 | 4        | 0,50    | 0,25  | 0,33      | 0,333  |
| NT-2111 | 4        | 0,52    | 0,25  | 0,37      | 0,360  |
| NT-2093 | 4        | 0,61    | 0,25  | 0,49      | 0,480  |
| NT-2135 | 2        | 0,97    | 0,50  | 0,93      | 0,940  |
| NT-2135 | 6        | 0,97    | 0,17  | 0,97      | 0,964  |

Über alle 100 Tickets gilt:

- Die Konfidenz bleibt höchstens so hoch wie der Prozentsatz der Wahl.
- Bei 55 Tickets stimmen beide Werte überein. Diese Tickets tragen 99 oder
  100 Prozent auf der gewählten Warteschlange. In diesem Bereich liefert die
  Formel denselben Wert.
- Bei 45 Tickets liegt die Konfidenz darunter.
- Die gewählte Option trägt in allen 100 Fällen den höchsten Prozentsatz.

Für Schwellen eignet sich deshalb `confidence`. Der Prozentsatz allein hängt
von der Anzahl der Optionen ab. Bei zwei Optionen steht 50 Prozent für reines
Raten, die Konfidenz beträgt 0. Bei zehn Optionen steht derselbe Prozentsatz
für eine deutliche Wahl, die Konfidenz beträgt 0,44. `RoutingPolicy` nutzt
deshalb `confidence`.

## Ein Lauf dauert 4,2 Sekunden und kostet 0,0041 USD

| Kennzahl      | Wert                                      |
|---------------|-------------------------------------------|
| Tickets       | 100                                       |
| Dauer         | 4,2 Sekunden, acht Tickets nebenläufig    |
| Eingabe-Token | 97.851                                    |
| Kosten        | 0,0041 USD bei 0,042 USD je Million Token |
| Modell        | jev-1.13.0                                |

Ein Aufruf je Ticket beantwortet alle vier Fragen. typesafe.ai berechnet allein
die Eingabe-Token. Es zählen der Ticket-Text und die Fragen. Ein Posteingang von
10.000 Tickets kostet nach dieser Messung 41 Cent.

## Die Tickets verteilen sich ungleich auf die vier Warteschlangen

| Warteschlange | Tickets |
|---------------|---------|
| technical     | 31      |
| billing       | 30      |
| sales         | 20      |
| contracts     | 19      |

Die folgende Aufstellung umfasst alle 100 Tickets. Die Tabelle im Abschnitt
zur Trefferquote zählt dagegen nur die 97 bewerteten Tickets.

| Bearbeitungsart   | Tickets |
|-------------------|---------|
| Standard handling | 65      |
| Review desk       | 14      |
| Rush handling     | 13      |
| Escalation        | 8       |

## Die Wahl bleibt bei 99 von 100 Tickets gleich

Der Aufruf `--repeat 3` bewertet jedes Ticket dreimal. Danach vergleicht er die
Zuordnungen:

```
Stability over 3 runs
  same queue every time  99 of 100
    NT-2081  technical×2, contracts×1
```

99 Tickets erhalten in jedem Lauf dieselbe Warteschlange. NT-2081 wechselt. Es
trägt die niedrigste Konfidenz aller 100 Tickets. Die Werte von `urgency`
weichen zwischen zwei Läufen um höchstens 0,13 ab.

Rechne bei jeder Schwelle mit dieser Schwankung von 0,13. Nenne bei Zahlen in
einem Bericht den Lauf, aus dem sie stammen.

## Der Ton weicht von der Sachlage ab

| Tonlage  | Tickets |
|----------|---------|
| Factual  | 74      |
| Tense    | 12      |
| Annoyed  | 10      |
| Outraged | 4       |

Neun Tickets melden eine dringende Sachlage in sachlichem Ton. Drei Tickets
schreiben scharf über ein geringes Anliegen.

| Ticket  | Anliegen                                            | urgency       | mood         |
|---------|-----------------------------------------------------|---------------|--------------|
| NT-2101 | Netzausfall im Gewerbegebiet, Spedition steht still | Immediate 2,8 | Factual 0,1  |
| NT-2072 | Notrufweiterleitung für 42 Heimbewohner ausgefallen | Urgent 2,4    | Factual 0,0  |
| NT-2053 | Zahnarztpraxis ohne Telefon und Internet            | Immediate 3,0 | Tense 0,7    |
| NT-2071 | Rechnung kam einen Tag zu spät, in Großbuchstaben   | Soon 0,5      | Outraged 2,7 |
| NT-2126 | Preiszusage nicht eingehalten, Vorwurf Betrug       | Soon 1,3      | Outraged 3,0 |
| NT-2089 | Kritik an der Telefonhotline                        | Routine 0,4   | Annoyed 2,0  |

Eine Sortierung nach `mood` stellt NT-2071 vor NT-2101. Eine Sortierung nach
`urgency` kehrt die Reihenfolge um. Die Demo trennt deshalb beide Skalen.

## Die Eskalation ist von der Zuordnung unabhängig

Acht Tickets überschreiten 60 Prozent Eskalationswahrscheinlichkeit. Ihre
Konfidenz bei der Warteschlange reicht von 18 bis 100 Prozent.

| Ticket  | Eskalation | Warteschlange | Konfidenz |
|---------|------------|---------------|-----------|
| NT-2047 | 94 %       | billing       | 100 %     |
| NT-2081 | 90 %       | contracts     | 18 %      |
| NT-2126 | 87 %       | billing       | 86 %      |
| NT-2118 | 84 %       | billing       | 100 %     |
| NT-2060 | 77 %       | contracts     | 97 %      |
| NT-2077 | 68 %       | billing       | 67 %      |
| NT-2138 | 64 %       | technical     | 86 %      |
| NT-2085 | 63 %       | contracts     | 100 %     |

NT-2081 zeigt den Nutzen getrennter Fragen. Die Warteschlange bleibt offen. Die
Eskalation steht fest.

## Der Score ist der Durchschnitt der Stufennummern

Die vier Stufen tragen die Nummern 0 bis 3: Routine 0, Soon 1, Urgent 2 und
Immediate 3. Jev verteilt auf diese vier Stufen zusammen 100 Prozent. Aus
dieser Verteilung entstehen zwei Werte.

`score` ist der Durchschnitt der Stufennummern. Jede Nummer zählt dabei mit
ihrem Prozentsatz. NT-2064 erhält 72 Prozent auf Urgent und 28 Prozent auf
Immediate. Die Rechnung lautet 2 × 0,72 + 3 × 0,28 = 2,28. Jev gibt 2,27 aus.
Die Abweichung entsteht durch die gerundete Ausgabe der Prozentsätze.

`confidence` ist der Prozentsatz der Stufe, auf die der `score` rundet.
NT-2064 rundet von 2,27 auf Stufe 2, also auf Urgent. Dort liegen 72 Prozent.
Die Konfidenz beträgt 0,72.

Die folgende Tabelle stammt aus einem eigenen Aufruf für sieben Tickets. Die
JSON-Ausgabe der Demo führt je Stufe allein Stufe, Wert und Konfidenz. Für die
Prozentsätze je Stufe braucht es diesen Aufruf. Die Werte weichen daher um
wenige Hundertstel vom Referenzlauf ab.

| Ticket  | `score` | Routine | Soon | Urgent | Immediate | Stufe     | `confidence` |
|---------|---------|---------|------|--------|-----------|-----------|--------------|
| NT-2043 | 0,00    | 1,00    | 0,00 | 0,00   | 0,00      | Routine   | 1,00         |
| NT-2041 | 1,42    | 0,02    | 0,54 | 0,44   | 0,00      | Soon      | 0,54         |
| NT-2103 | 1,59    | 0,01    | 0,39 | 0,60   | 0,00      | Urgent    | 0,58         |
| NT-2120 | 1,99    | 0,01    | 0,04 | 0,91   | 0,04      | Urgent    | 0,91         |
| NT-2091 | 2,01    | 0,00    | 0,00 | 0,98   | 0,02      | Urgent    | 0,98         |
| NT-2064 | 2,27    | 0,00    | 0,00 | 0,72   | 0,28      | Urgent    | 0,72         |
| NT-2046 | 2,47    | 0,00    | 0,00 | 0,52   | 0,48      | Urgent    | 0,51         |

Die Nachkommastelle misst den Abstand zur benannten Stufe. Sie gibt zugleich
die Richtung an.

- Ein Wert nahe ,0 steht für eine eindeutige Stufe. NT-2091 trägt 2,01 und
  legt 98 Prozent auf Urgent.
- Ein Wert nahe ,5 steht für zwei gleich starke Nachbarstufen. NT-2046 trägt
  2,47 und verteilt 52 Prozent auf Urgent und 48 Prozent auf Immediate.
- Ein Wert dazwischen zeigt die Neigung zur Nachbarstufe. NT-2064 trägt 2,27
  und legt 28 Prozent auf Immediate.

`confidence` und Nachkommastelle beantworten verschiedene Fragen.
`confidence` gibt an, wie sicher die benannte Stufe ist. Die Nachkommastelle
gibt an, zu welcher Nachbarstufe die Unsicherheit zeigt. NT-2041 und NT-2103
tragen fast dieselbe Konfidenz. Sie liegen auf verschiedenen Stufen und neigen
in verschiedene Richtungen.

Aus der Nachkommastelle entsteht eine Rangfolge innerhalb einer Stufe. Die
Stufe Urgent umfasst 17 Tickets. Ihre Werte reichen von 1,54 bis 2,44. Eine
Sortierung nach `score` stellt NT-2046 vor NT-2103. Eine Sortierung nach der
Stufe behandelt beide gleich.

`Urgency` hält deshalb den Rohwert in `value`. Die Rundung auf eine benannte
Stufe erfolgt erst beim Zugriff auf `level`.

Die Werte schwanken zwischen Läufen um wenige Hundertstel. NT-2046 trug in
zwei Läufen 2,44 und 2,47. Die Stufe bleibt dabei gleich.

## Die Skala von mood erfasst allein die Schärfe

NT-2073, NT-2086 und NT-2121 enthalten Lob. Alle drei erhalten Factual 0,0.
Die vier Stufen reichen von Factual bis Outraged. Freude liegt außerhalb
dieser Reihe. Für die Erkennung von Lob eignet sich eine eigene `noul`-Frage.

## Aufgezeichnete Antworten liest man als JSON-Text ein

Lies aufgezeichnete Antworten als JSON-Text ein. Die Antwortmodelle des SDK
prüfen mit `strict=True`. Sie erwarten die Stufennummern einer Score-Antwort
als Zahlen. JSON kennt jedoch allein Zeichenketten als Schlüssel.
`model_validate_json` wandelt diese Zeichenketten in Zahlen um. Der Weg über
`json.loads` und `model_validate` scheitert daran.
