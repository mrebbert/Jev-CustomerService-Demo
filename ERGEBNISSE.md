# Was die Jev-Läufe über die 50 Demo-Tickets zeigen

Alle Zahlen stammen aus Läufen vom 21. und 22. September 2026 gegen
`jev-1.13.0`. Die Tickets stehen in `data/tickets.yaml`, den Lauf startet
`python -m routing.cli`.

## Ein Lauf kostet zwei Sekunden und einen Fünftel Cent

| Kennzahl        | Wert                                        |
|-----------------|---------------------------------------------|
| Tickets         | 50                                          |
| Dauer           | 2,4 Sekunden, acht Tickets nebenläufig      |
| Eingabe-Token   | 48.165                                      |
| Kosten          | 0,0020 USD bei 0,042 USD je Million Token   |
| Modell          | jev-1.13.0                                  |

Ein Aufruf je Ticket beantwortet alle vier Fragen. Ausgabe-Token berechnet
typesafe.ai nicht, daher zählt allein der Ticketext plus die Fragen.

## Die Last verteilt sich ungleich auf die vier Teams

| Warteschlange  | Tickets |
|----------------|---------|
| technik        | 18      |
| abrechnung     | 13      |
| vertragswesen  | 11      |
| vertrieb       | 8       |

| Nächster Schritt | Tickets |
|------------------|---------|
| Regelbearbeitung | 28      |
| Eilbearbeitung   | 12      |
| Eskalation       | 5       |
| Sichtprüfung     | 5       |

## Der Ton folgt der Sachlage nicht

| Tonlage      | Tickets |
|--------------|---------|
| Sachlich     | 35      |
| Angespannt   | 7       |
| Verärgert    | 6       |
| Aufgebracht  | 2       |

Sechs Tickets melden eine ernste Lage in ruhigem Ton, zwei schreiben scharf
über eine Kleinigkeit. Die Gegenüberstellung trägt die ganze Demo:

| Ticket  | Anliegen                                          | Dringlichkeit | Stimmung              |
|---------|---------------------------------------------------|---------------|-----------------------|
| NT-2071 | Rechnung kam einen Tag zu spät, in Großbuchstaben | Routine 0,5   | Aufgebracht 2,7 (67 %) |
| NT-2072 | Notrufweiterleitung für 42 Heimbewohner ausgefallen | Dringend 2,3 | Sachlich 0,0 (100 %)  |
| NT-2053 | Zahnarztpraxis ohne Telefon und Internet          | Sofort 3,0    | Angespannt 0,7 (72 %) |
| NT-2077 | Sperre bei stillstehendem Onlineshop              | Sofort 3,0    | Aufgebracht 2,9 (91 %) |

Wer nach Lautstärke sortiert, nimmt NT-2071 vor NT-2072. Die getrennten Skalen
drehen das um. NT-2077 zeigt den Fall, in dem beide zusammenfallen.

## Eine unsichere Zuordnung meldet sich selbst

| Ticket  | Betreff                              | Konfidenz | Was das Modell sagt                                      |
|---------|--------------------------------------|-----------|----------------------------------------------------------|
| NT-2081 | Letzte Warnung vor der Verbraucherzentrale | 13 %  | Team offen zwischen Abrechnung und Vertragswesen, Eskalation dagegen bei 90 % |
| NT-2080 | Vertrag läuft weiter, obwohl gekündigt | 37 %    | Vertragsfrage und Erstattung zugleich                     |
| NT-2074 | Ich gebe auf                          | 51 %      | Resignation ohne klares Anliegen                          |
| NT-2088 | Geschwindigkeit unter der Zusage      | 66 %      | Technische Messung mit Entgeltminderung                   |
| NT-2068 | Neuer Anschluss für Ferienwohnung     | 78 %      | Neugeschäft mit Bereitstellungsfrage                      |

NT-2081 zeigt den Nutzen getrennter Fragen am deutlichsten: Das Team bleibt
offen, die Chefsache steht fest.

## Die Schwelle für die Sichtprüfung kostet Handarbeit

Ein Vergleich über dieselben Tickets, allein `--mindestkonfidenz` verschoben:

| Schwelle | Sichtprüfung | Anteil |
|----------|--------------|--------|
| 0,80     | 5 von 50     | 10 %   |
| 0,95     | 12 von 50    | 24 %   |

Die Zuordnung auf die Teams bleibt dabei gleich. Die Schwelle steuert allein,
wer nachsieht. Bei 0,95 fängt die Leitstelle jedes Mischanliegen ab und zahlt
dafür mit mehr als dem doppelten Aufwand.

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

## Drei Beobachtungen für den Nachbau

**Die Skala kennt keine Freude.** NT-2073 und NT-2086 sind Lob und landen beide
bei Sachlich 0,0. Die Stufen messen allein die Schärfe. Wer Dankesschreiben
erkennen will, stellt dafür eine eigene `noul`-Frage.

**Die Antworten schwanken leicht.** NT-2068 lag über mehrere Läufe zwischen 78
und 82 Prozent. Die Rangfolge der Grenzfälle bleibt stabil, die zweite
Nachkommastelle nicht. Wer Schwellen setzt, plant diesen Spielraum ein.

**Aufgezeichnete Antworten liest man als JSON-Text.** Die Antwortmodelle des SDK
laufen mit `strict=True`, und die Stufenschlüssel einer Score-Antwort gelten als
Zahlen. `model_validate_json` rechnet die Zeichenketten des Formats selbst um,
der Umweg über `json.loads` und `model_validate` scheitert daran.
