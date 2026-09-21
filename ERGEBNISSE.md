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

Die Escalation hat Vorrang vor der Review desk. Die Review desk hat Vorrang
vor der Rush handling.

## Jev trifft 92 Prozent der Zuordnungen

Jedes Ticket trägt im Feld `expected` die Warteschlange, die ein Disponent
wählt. Der Lauf hält dieses Feld vom Modell fern. Es dient allein der
Bewertung. Drei Tickets mit unklarem Fachthema bleiben außerhalb der Wertung:
NT-2074, NT-2121 und NT-2124.

| Kennzahl                 | Wert        |
|--------------------------|-------------|
| bewertete Tickets        | 97          |
| Treffer                  | 89 (91,8 %) |
| Fehler                   | 8           |
| Median-Konfidenz Treffer | 1,00        |
| Median-Konfidenz Fehler  | 0,62        |

Die beiden Mediane zeigen den Zusammenhang: Bei richtigen Zuordnungen meldet
Jev hohe Konfidenz. Bei falschen Zuordnungen meldet Jev niedrige Konfidenz.

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

Ab Schwelle 0,90 arbeitet die Automatik fehlerfrei. Der Preis beträgt sechs
zusätzliche Prüfungen. Die Review desk steigt von 13 auf 19 Tickets.

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
beschreibt diesen Zustand zutreffend. Der Zuschnitt der Warteschlangen lässt
diese Anliegen offen.

## Die Konfidenz ist die auf den Zufall normierte Wahrscheinlichkeit

Eine `choice`-Antwort liefert zwei Größen mit verschiedener Bedeutung.

`probabilities` verteilt die Wahrscheinlichkeit auf alle Optionen. Die Summe
beträgt 1,0. Der Wert je Option gibt an, wie stark das Modell diese Option
stützt.

`confidence` gilt allein für die gewählte Option. Der Wert misst den Abstand
zum Zufall.

Die Messung ergibt eine feste Umrechnung zwischen beiden Größen:

```
confidence = (p - 1/n) / (1 - 1/n)       n = Anzahl der Optionen
                                         p = Wahrscheinlichkeit der Wahl
```

Umfang der Prüfung: 100 Antworten mit vier Optionen aus vier Läufen, dazu je
eine Antwort mit zwei, drei und sechs Optionen. Die mittlere Abweichung
beträgt 0,0026. Die größte Abweichung beträgt 0,0100. Sie entspricht der
Rundung auf zwei Nachkommastellen in der Ausgabe.

| Ticket  | Optionen | p(Wahl) | Konfidenz | Formel |
|---------|----------|---------|-----------|--------|
| NT-2081 | 4        | 0,32    | 0,10      | 0,093  |
| NT-2135 | 4        | 0,50    | 0,33      | 0,333  |
| NT-2111 | 4        | 0,52    | 0,37      | 0,360  |
| NT-2093 | 4        | 0,61    | 0,49      | 0,480  |
| NT-2135 | 2        | 0,97    | 0,93      | 0,940  |
| NT-2135 | 6        | 0,97    | 0,97      | 0,964  |

Daraus folgen drei Aussagen über den gesamten Stapel:

- Die Konfidenz bleibt höchstens so hoch wie die Wahrscheinlichkeit der Wahl.
- Bei 55 von 100 Tickets stimmen beide Werte überein. Diese Tickets tragen die
  Wahrscheinlichkeit 0,99 oder 1,00. Bei diesen Werten liefert die Formel
  dasselbe Ergebnis.
- Bei 45 Tickets liegt die Konfidenz darunter.
- Die gewählte Option ist in allen 100 Fällen die wahrscheinlichste.

Für Schwellen eignet sich deshalb `confidence`. Die rohe Wahrscheinlichkeit
hängt von der Anzahl der Optionen ab. Bei zwei Optionen bedeutet 0,50 reines
Raten. Bei zehn Optionen bedeutet derselbe Wert eine deutliche Präferenz. Die
Konfidenz gleicht diesen Unterschied aus. `RoutingPolicy` nutzt diesen Wert.

## Ein Lauf dauert 4,2 Sekunden und kostet 0,0041 USD

| Kennzahl      | Wert                                      |
|---------------|-------------------------------------------|
| Tickets       | 100                                       |
| Dauer         | 4,2 Sekunden, acht Tickets nebenläufig    |
| Eingabe-Token | 97.851                                    |
| Kosten        | 0,0041 USD bei 0,042 USD je Million Token |
| Modell        | jev-1.13.0                                |

Ein Aufruf je Ticket beantwortet alle vier Fragen. typesafe.ai berechnet allein
die Eingabe-Token. Es zählen der Ticketext und die Fragen. Ein Posteingang von
10.000 Tickets kostet nach dieser Messung 41 Cent.

## Die Tickets verteilen sich ungleich auf die vier Warteschlangen

| Warteschlange | Tickets |
|---------------|---------|
| technical     | 31      |
| billing       | 30      |
| sales         | 20      |
| contracts     | 19      |

| Bearbeitungsart   | Tickets |
|-------------------|---------|
| Standard handling | 65      |
| Review desk       | 15      |
| Rush handling     | 13      |
| Escalation        | 7       |

## Die Wahl bleibt bei 99 von 100 Tickets gleich

Der Aufruf `--repeat 3` bewertet jedes Ticket dreimal. Danach vergleicht er die
Zuordnungen:

```
Stability over 3 runs
  same queue every time  99 of 100
    NT-2081  technical×2, contracts×1
```

99 Tickets erhalten in jedem Lauf dieselbe Warteschlange. NT-2081 wechselt. Es
trägt die niedrigste Konfidenz im gesamten Stapel. Die Werte von `urgency`
weichen zwischen zwei Läufen um höchstens 0,13 ab.

Setze Schwellen mit Abstand zu diesem Spielraum. Nenne bei Zahlen in einem
Bericht den Lauf, aus dem sie stammen.

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

Sieben Tickets überschreiten 60 Prozent Eskalationswahrscheinlichkeit. Ihre
Konfidenz bei der Warteschlange reicht von 14 bis 100 Prozent.

| Ticket  | Eskalation | Warteschlange | Konfidenz |
|---------|------------|---------------|-----------|
| NT-2047 | 93 %       | billing       | 100 %     |
| NT-2081 | 90 %       | contracts     | 14 %      |
| NT-2126 | 87 %       | billing       | 88 %      |
| NT-2118 | 85 %       | billing       | 100 %     |
| NT-2060 | 76 %       | contracts     | 96 %      |
| NT-2077 | 70 %       | billing       | 86 %      |
| NT-2138 | 61 %       | technical     | 93 %      |

NT-2081 zeigt den Nutzen getrennter Fragen. Die Warteschlange bleibt offen. Die
Eskalation steht fest.

## Der Score ist ein Erwartungswert

Jev gibt bei einer `score`-Frage die Verteilung über alle Stufen zurück. Der
Wert `score` ist der gewichtete Mittelwert dieser Verteilung.

| Ticket  | Verteilung über Routine, Soon, Urgent, Immediate | `score` | Summe(Stufe × p) |
|---------|--------------------------------------------------|---------|------------------|
| NT-2043 | 1,00 / 0 / 0 / 0                                 | 0,00    | 0,00             |
| NT-2041 | 0,01 / 0,51 / 0,48 / 0                           | 1,46    | 1,47             |
| NT-2046 | 0 / 0 / 0,56 / 0,44                              | 2,43    | 2,44             |
| NT-2053 | 0 / 0 / 0 / 1,00                                 | 3,00    | 3,00             |

Die Abweichung von einem Hundertstel entsteht durch die gerundete Ausgabe der
Wahrscheinlichkeiten.

Die Nachkommastelle trägt Information. NT-2041 liegt mit 1,46 zwischen Soon und
Urgent. NT-2046 liegt mit 2,43 deutlich über der Grenze zu Urgent. `Urgency`
hält deshalb den Rohwert. Die Rundung auf eine benannte Stufe erfolgt erst bei
der Ausgabe.

## Zwei Hinweise für den Nachbau

Die Skala von `mood` erfasst allein die Schärfe. NT-2073, NT-2086 und NT-2121
enthalten Lob. Alle drei erhalten Factual 0,0. Für die Erkennung von Lob eignet
sich eine eigene `noul`-Frage.

Lies aufgezeichnete Antworten als JSON-Text ein. Die Antwortmodelle des SDK
prüfen mit `strict=True`. Die Stufenschlüssel einer Score-Antwort gelten dabei
als Zahlen. `model_validate_json` wandelt die Zeichenketten des Formats in
diese Zahlen um. Der Weg über `json.loads` und `model_validate` scheitert.
