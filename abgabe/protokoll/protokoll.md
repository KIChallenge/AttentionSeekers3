# Protokoll der Änderungen

Automatisch erzeugt aus `ops.change_log` (`python -m statagent protokoll`). Jede Änderung an Regeln, Code oder Lieferungen mit Anweisung, freigebender Person und Zeitpunkt; Vorschläge der Agenten erscheinen ohne freigebende Person, bis eine Person entscheidet. Die Spalte Commit wird aus der git-Historie ergänzt.

| Nr. | Zeitpunkt | Objekt | Änderung | Anweisung | Freigegeben von | Commit |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | 2026-11-05 14:59 | rule:R-DQ01 | Regel R-DQ01 freigegeben: Lieferung 2025-06: BEGINN und ENDE vertauscht lesen |  | Mercy |  |
| 2 | 2026-11-05 15:45 | rule:R-DQ07 | Regel R-DQ07 freigegeben: Veraltete ÖNACE-2003-Codes DA–DM dem Abschnitt C zuordnen | ÖNACE-2003-Codes DA–DM dem Abschnitt C zuordnen | Mercy |  |
| 3 | 2026-11-05 15:45 | rule:R-DQ08 | Regel R-DQ08 freigegeben: Leere Merkmale der Ausprägung „unbekannt“ zuordnen | Leere Merkmale der Ausprägung unbekannt zuordnen | Mercy |  |
| 15 | 2026-11-05 21:09 | rule:R-DQ05 | Regelvorschlag R-DQ05 überarbeitet (noch nicht freigegeben): birth_date_swap statt age_from_birth_year | Geburtsdatum mit Monat 13 als falsches Format markieren, Tag und Monat vertauscht lesen, Ausschluss wählbar |  |  |
| 17 | 2026-11-05 23:19 | rule:R-DQ03 | Regel R-DQ03 freigegeben: Exakt doppelte Sätze nur einmal berücksichtigen | Exakt doppelte Saetze = technische Doppellieferung; jedes Verhaeltnis zaehlt einmal (Anhang A Regel 1), Kopien bleiben markiert. | Mercy |  |
| 18 | 2026-11-05 23:20 | rule:R-DQ05 | Regel R-DQ05 freigegeben: Geburtsdatum mit Monat 13: als falsches Datumsformat markieren, Tag und Monat vertauscht lesen | Monat 13 = falsches Datumsformat; Tag/Monat getauscht lesen, sonst Alter unbekannt; kein Verhaeltnis geht verloren. | Mercy |  |
| 19 | 2026-11-05 23:20 | rule:R-DQ09 | Regel R-DQ09 freigegeben: Überlappende Abschnitte: der spätere gilt ab seinem Beginn | Ueberlappung: spaeterer Abschnitt gilt ab seinem Beginn (Fachbeschreibung 2); Verhaeltnis zaehlt einmal. | Mercy |  |
| 20 | 2026-11-06 00:22 | month:basis:2024-08 | Berichtsmonat 2024-08 (basis) veröffentlicht, Lauf 148 |  | Mercy |  |
| 21 | 2026-11-06 00:22 | month:basis:2024-09 | Berichtsmonat 2024-09 (basis) veröffentlicht, Lauf 149 |  | Mercy |  |
| 22 | 2026-11-06 00:22 | month:basis:2024-10 | Berichtsmonat 2024-10 (basis) veröffentlicht, Lauf 150 |  | Mercy |  |
| 23 | 2026-11-06 00:22 | month:basis:2024-11 | Berichtsmonat 2024-11 (basis) veröffentlicht, Lauf 151 |  | Mercy |  |
| 24 | 2026-11-06 00:22 | month:basis:2024-12 | Berichtsmonat 2024-12 (basis) veröffentlicht, Lauf 152 |  | Mercy |  |
| 25 | 2026-11-06 00:22 | month:basis:2025-01 | Berichtsmonat 2025-01 (basis) veröffentlicht, Lauf 153 |  | Mercy |  |
| 26 | 2026-11-06 00:22 | month:basis:2025-02 | Berichtsmonat 2025-02 (basis) veröffentlicht, Lauf 154 |  | Mercy |  |
| 27 | 2026-11-06 00:22 | month:basis:2025-03 | Berichtsmonat 2025-03 (basis) veröffentlicht, Lauf 155 |  | Mercy |  |
| 28 | 2026-11-06 00:22 | month:basis:2025-04 | Berichtsmonat 2025-04 (basis) veröffentlicht, Lauf 156 |  | Mercy |  |
| 29 | 2026-11-06 00:22 | month:basis:2025-05 | Berichtsmonat 2025-05 (basis) veröffentlicht, Lauf 157 |  | Mercy |  |
| 30 | 2026-11-06 00:22 | month:basis:2025-06 | Berichtsmonat 2025-06 (basis) veröffentlicht, Lauf 158 |  | Mercy |  |
| 31 | 2026-11-06 00:22 | month:basis:2025-07 | Berichtsmonat 2025-07 (basis) veröffentlicht, Lauf 159 |  | Mercy |  |
| 32 | 2026-11-06 00:22 | month:basis:2025-08 | Berichtsmonat 2025-08 (basis) veröffentlicht, Lauf 160 |  | Mercy |  |
| 33 | 2026-11-06 00:22 | month:basis:2025-09 | Berichtsmonat 2025-09 (basis) veröffentlicht, Lauf 161 |  | Mercy |  |
| 34 | 2026-11-06 00:22 | month:basis:2025-10 | Berichtsmonat 2025-10 (basis) veröffentlicht, Lauf 162 |  | Mercy |  |
| 35 | 2026-11-06 00:22 | month:basis:2025-11 | Berichtsmonat 2025-11 (basis) veröffentlicht, Lauf 163 |  | Mercy |  |
| 36 | 2026-11-06 00:22 | month:basis:2025-12 | Berichtsmonat 2025-12 (basis) veröffentlicht, Lauf 164 |  | Mercy |  |
| 37 | 2026-11-06 00:22 | month:basis:2026-01 | Berichtsmonat 2026-01 (basis) veröffentlicht, Lauf 165 |  | Mercy |  |
| 38 | 2026-11-06 00:22 | month:basis:2026-02 | Berichtsmonat 2026-02 (basis) veröffentlicht, Lauf 166 |  | Mercy |  |
| 39 | 2026-11-06 00:22 | month:basis:2026-03 | Berichtsmonat 2026-03 (basis) veröffentlicht, Lauf 167 |  | Mercy |  |
| 40 | 2026-11-06 00:22 | month:basis:2026-04 | Berichtsmonat 2026-04 (basis) veröffentlicht, Lauf 168 |  | Mercy |  |
| 41 | 2026-11-06 00:22 | month:basis:2026-05 | Berichtsmonat 2026-05 (basis) veröffentlicht, Lauf 169 |  | Mercy |  |
| 42 | 2026-11-06 00:22 | month:basis:2026-06 | Berichtsmonat 2026-06 (basis) veröffentlicht, Lauf 170 |  | Mercy |  |
| 43 | 2026-11-06 00:22 | month:basis:2026-07 | Berichtsmonat 2026-07 (basis) veröffentlicht, Lauf 171 |  | Mercy |  |
| 51 | 2026-11-06 02:50 | backup:statistik_2026-11-06_0248.dump | Sicherung statistik_2026-11-06_0248.dump (0.51 GB, SHA-256 81a517d76f7a3503…, 10,152,292 Lieferzeilen) | Datenbank sichern |  |  |
| 53 | 2026-11-06 03:24 | rule:R-A1 | Regel R-A1 vorgeschlagen von Agent Klassifikation (noch nicht wirksam): Änderungsauftrag 1: Beschäftigungskategorie nur noch Arbeiter, Angestellte, Beamte | „Auftrag 1: Unterscheide in Statistik und Aggregations-Sheet nicht mehr zwischen Dienstvertrag und freiem Dienstvertrag – nur noch Arbeiter, Angestellte und Beamte, rückwirkend für die ganze Zeitreihe.“ |  |  |
| 54 | 2026-11-06 03:24 | rule:R-A1 | Regel R-A1 freigegeben: Änderungsauftrag 1: Beschäftigungskategorie nur noch Arbeiter, Angestellte, Beamte |  | Test User |  |
| 55 | 2026-11-06 03:25 | rule:R-A2 | Regel R-A2 vorgeschlagen von Agent Datenmanagement (noch nicht wirksam): Änderungsauftrag 2: ganzes Monat statt Stichtag | „Auftrag 2: Zähle das ganze Monat statt des Stichtags – beschäftigt ist, wer im Berichtsmonat mindestens einen Tag beschäftigt war.“ |  |  |
| 56 | 2026-11-06 03:25 | rule:R-A2 | Regel R-A2 freigegeben: Änderungsauftrag 2: ganzes Monat statt Stichtag |  | Test User |  |
| 57 | 2026-11-06 03:25 | rule:R-A3 | Regel R-A3 vorgeschlagen von Agent Reporting (noch nicht wirksam): Änderungsauftrag 3: Lieferung an das Ministerium (Arbeiter in Abschnitt C, ≥ 200 Tage) | „Auftrag 3: Erstelle die Ministeriums-Lieferung für 07/2026 – Personen mit mindestens 200 Tagen als Arbeiter (DV oder FD) in ÖNACE-Abschnitt C in den letzten zwölf Monaten.“ |  |  |
| 58 | 2026-11-06 03:26 | rule:R-A3 | Regel R-A3 freigegeben: Änderungsauftrag 3: Lieferung an das Ministerium (Arbeiter in Abschnitt C, ≥ 200 Tage) |  | Test User |  |
| 60 | 2026-11-06 06:54 | rule_set:auftraege | Regelwerk Aufträge gerechnet (24 Monate) nach den freigegebenen Regeln R-A1, R-A2 | Setze die freigegebenen Aufträge um | Test User |  |
| 61 | 2026-11-06 06:54 | delivery:abgabe/ministerium_2026-07.csv | Ministeriums-Lieferung abgabe/ministerium_2026-07.csv erzeugt: 32741 Personen, SHA-256 c7c6f52dfd4251ee… – wartet auf Freigabe der Lieferung | Setze die freigegebenen Aufträge um | Test User |  |
| 62 | 2026-11-06 07:30 | delivery:abgabe/ministerium_2026-07.csv | Lieferung abgabe/ministerium_2026-07.csv freigegeben (SHA-256 c7c6f52dfd4251ee…) |  | Test User |  |
