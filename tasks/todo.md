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

- [ ] 1. Gerüst anlegen: venv, .gitignore, requirements.txt, .env.example, README
- [ ] 2. Domänenmodell in `src/routing/domain.py` schreiben, dazu Tests
- [ ] 3. Anti-Corruption Layer `src/routing/jev_client.py` gegen typesafe-sdk
- [ ] 4. Anwendungsfall `src/routing/router.py`, Jev-Antwort auf RoutingDecision abbilden
- [ ] 5. 30 deutsche Demo-Tickets als `data/tickets.yaml` schreiben
- [ ] 6. CLI `python -m routing.cli`: Tickets laden, routen, Tabelle ausgeben
- [ ] 7. Tests mit Fake-Jev-Antworten, kein Netz im Testlauf
- [ ] 8. README mit Ablauf, Schlüsselvergabe und Beispielausgabe

## Entscheidungen

- Der Jev-Zugang liegt in `.env` als `TYPESAFE_API_KEY`, geladen über python-dotenv.
  Die `.env` bleibt außerhalb von Git, `.env.example` zeigt die Form.
- Die Demo-Texte stehen fest im Repo. Damit läuft die Demo mit einem einzigen
  Schlüssel und liefert bei jedem Lauf dieselbe Ausgangslage.
- `jev_client` kapselt das SDK vollständig. Die Domäne kennt kein Jev-Feld.

## Offene Eingangsgröße

- `TYPESAFE_API_KEY` fehlt noch. Bis er vorliegt, laufen Aufbau und Tests
  gegen aufgezeichnete Antworten.
