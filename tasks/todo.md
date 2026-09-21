# Ticket-Routing mit Jev: Plan

## Der Bounded Context heißt Ticket-Routing

Ein eingehendes Ticket trägt Freitext. Der Context entscheidet, welches
Team es bearbeitet, wie dringend es ist und ob es eskaliert. Jev liefert
diese Entscheidung als typisierte Antwort mit Wahrscheinlichkeiten.

### Domänenmodell

| Begriff         | Art          | Inhalt                                                        |
|-----------------|--------------|---------------------------------------------------------------|
| Ticket          | Entity       | Kennung, Betreff, Text, Eingangszeit                          |
| Queue           | Enum         | abrechnung, technik, vertrieb, vertragswesen                  |
| Urgency         | Value Object | Stufe 0 bis 3 mit Legende, plus Konfidenz                     |
| RoutingDecision | Value Object | Queue, Konfidenz, Wahrscheinlichkeiten, Urgency, Eskalation   |
| RoutingPolicy   | Domain Service | Legt fest, ab welcher Konfidenz ein Mensch nachsieht        |

### Jev-Anfrage je Ticket

Ein Aufruf, drei Fragen parallel:

- `queue` als `choice` über die vier Teams, criteria beschreibt jedes Team
- `urgency` als `score` mit vier Stufen von "Routine" bis "Sofort"
- `needs_escalation` als `noul` für Vertragsbruch, Kündigungsdrohung, Rechtsbezug

## Aufgabenliste

- [x] 1. Gerüst anlegen: venv, .gitignore, requirements.txt, .env.example, README
- [x] 2. Domänenmodell in `src/routing/domain.py` schreiben, dazu Tests
- [x] 3. Anti-Corruption Layer `src/routing/jev_client.py` gegen typesafe-sdk
- [x] 4. Anwendungsfall `src/routing/router.py`, Jev-Antwort auf RoutingDecision abbilden
- [x] 5. 30 deutsche Demo-Tickets als `data/tickets.yaml` schreiben
- [x] 6. CLI `python -m routing.cli`: Tickets laden, routen, Tabelle ausgeben
- [x] 7. Tests mit Fake-Jev-Antworten, kein Netz im Testlauf
- [x] 8. README mit Ablauf, Schlüsselvergabe und Beispielausgabe

## Entscheidungen

- Der Jev-Zugang liegt in `.env` als `TYPESAFE_API_KEY`, geladen über python-dotenv.
  Die `.env` bleibt außerhalb von Git, `.env.example` zeigt die Form.
- Die Demo-Texte stehen fest im Repo. Damit läuft die Demo mit einem einzigen
  Schlüssel und liefert bei jedem Lauf dieselbe Ausgangslage.
- `jev_client` kapselt das SDK vollständig. Die Domäne kennt kein Jev-Feld.

## Offene Eingangsgröße

- `TYPESAFE_API_KEY` fehlt noch. Bis er vorliegt, laufen Aufbau und Tests
  gegen aufgezeichnete Antworten.

## Ergebnis vom 21.09.2026

Die Demo läuft vollständig. Ein Lauf über alle 30 Tickets dauert rund zwei
Sekunden und kostet 0,0010 USD bei 24.522 Eingabe-Token.

- Die Verteilung fällt ausgewogen aus: Technik 9, Vertragswesen 8,
  Abrechnung 7, Vertrieb 6.
- Jev erkennt beide gebauten Eskalationsfälle, NT-2047 mit 93 Prozent und
  NT-2060 mit 75 Prozent.
- Der Grenzfall NT-2068 bleibt mit 78 Prozent unter der Schwelle und geht in
  die Sichtprüfung. Genau dafür dienen die kalibrierten Wahrscheinlichkeiten.
- 21 Tests laufen ohne Netz gegen eine aufgezeichnete Antwort.

### Was auffiel

- Der `score` ist der Erwartungswert über die Stufenverteilung, nicht die
  wahrscheinlichste Stufe. Nachgerechnet an NT-2046: 0.56 auf Dringend und
  0.44 auf Sofort ergeben 2.43. `Urgency` hält diesen Wert und rundet erst
  für die Anzeige auf eine benannte Stufe. Damit bleibt die Reihenfolge
  innerhalb einer Stufe erhalten.
- Die Antwortmodelle des SDK laufen mit `strict=True`. Eine aufgezeichnete
  Antwort liest man daher über `model_validate_json` aus dem JSON-Text.
  Dieser Weg rechnet die Stufenschlüssel von Zeichenkette in Zahl um, der
  Umweg über `json.loads` und `model_validate` scheitert daran.

## Erweiterung vom 21.09.2026: Stimmung und 50 Tickets

Jev beantwortet jetzt vier Fragen je Aufruf. Die neue `score`-Frage `stimmung`
misst den Ton von Sachlich bis Aufgebracht und liefert Wert und Konfidenz.
Die Ticketablage wuchs auf 50 Einträge.

- [x] `Mood` und `MoodLevel` im Domänenmodell, dazu `ton_ueber_sache`
- [x] Vierte Frage in `baue_fragen`, Übersetzung in `zu_entscheidung`
- [x] Spalte Stimmung in der Tabelle, Tonlage in der Zusammenfassung, JSON erweitert
- [x] 20 Tickets ergänzt, in denen Ton und Sachlage auseinanderlaufen
- [x] 8 Tests ergänzt, Aufzeichnung um die Stimmungsantwort erweitert

### Ergebnis

Ein Lauf über 50 Tickets dauert 2,4 Sekunden und kostet 0,0020 USD bei
48.165 Eingabe-Token. Die Tonlage verteilt sich auf 35 sachliche,
7 angespannte, 6 verärgerte und 2 aufgebrachte Tickets.

- Die Richtlinie bleibt unverändert. Der Ton beschreibt, er entscheidet nicht.
  Ein Test hält das fest: Gleiche Sachlage, anderer Ton, gleicher Schritt.
- NT-2071 schreibt aufgebracht über eine Kleinigkeit, NT-2072 meldet sachlich
  den Ausfall einer Notrufweiterleitung. Genau diese Paarung trennt die beiden
  Skalen sichtbar.
- NT-2081 zeigt eine Warteschlange mit 13 Prozent Konfidenz bei 90 Prozent
  Eskalation. Das Modell sagt sauber: Team unklar, Chefsache klar.
- Die Schärfeskala kennt kein Lob. NT-2073 und NT-2086 landen bei Sachlich 0.0.
  Für Dankesschreiben wäre eine eigene `noul`-Frage nötig.
