# Änderungsaufträge

Die Aufträge gelten ab Freitag. Liefert zuerst die Statistik nach den bisherigen Regeln.

**Die Änderungen setzen eure eigenen Agenten um, nicht euer Entwicklungswerkzeug.** Claude Code, Codex, Cursor und Ähnliches dürft ihr verwenden, um euer System zu bauen. Die drei Aufträge – die Umstellung der Kategorien, die neue Zählregel und die Lieferung an das Ministerium – gebt ihr aber als Anweisung in Sprache an die Agenten, die ihr selbst programmiert habt. Diese Agenten ändern Regeln oder Code, erzeugen die Lieferung und halten jede Änderung nachvollziehbar fest (Anweisung, was geändert wurde, Freigabe). Bei der Fachjury zeigt ihr das live mit einer weiteren, unbekannten Änderung.

Nach jeder Umstellung laufen die Monate wieder einzeln durch (siehe Fachbeschreibung, Monatsbetrieb).

## Auftrag 1 – Dienstvertrag und freier Dienstvertrag zusammen

In der Statistik und im Aggregations-Sheet wird nicht mehr zwischen Dienstvertrag (DV) und freiem Dienstvertrag (FD) unterschieden. Die Beschäftigungskategorie hat nur noch die Ausprägungen Arbeiter, Angestellte und Beamte (siehe Spalte BESCHAEFTIGUNGSKATEGORIE in `qualifikation.csv`). Die Änderung gilt rückwirkend für die ganze Zeitreihe.

## Auftrag 2 – Ganzes Monat statt Stichtag

Gezählt wird nicht mehr der Monatsletzte, sondern das ganze Monat: Beschäftigt ist, wer im Berichtsmonat jemals beschäftigt war. Auch ein einziger Tag mitten im Monat genügt.

| Punkt | Festlegung |
| --- | --- |
| Zählregel | Ein Verhältnis zählt, wenn mindestens ein Zeitabschnitt mindestens einen Tag im Berichtsmonat besteht: Beginn ≤ Monatsletzter und Ende leer oder ≥ Monatserster. |
| Zähleinheit | weiterhin Versicherungsverhältnisse; jedes Verhältnis zählt im Monat genau einmal |
| Merkmale | aus dem letzten Zeitabschnitt des Verhältnisses im Berichtsmonat |
| Alter | in vollendeten Jahren am Monatsletzten |
| Lieferung | weiterhin die Lieferung des Berichtsmonats |
| Geltung | rückwirkend für die ganze Zeitreihe, zusammen mit Auftrag 1 |

## Auftrag 3 – Datenlieferung an das Ministerium

Das Ministerium erhält eine Liste aller Personen, die in den letzten zwölf Monaten bis einschließlich Berichtsmonat mindestens 200 Tage als Arbeiter beschäftigt waren, mit Dienstvertrag oder freiem Dienstvertrag (ArbeiterDV, ArbeiterFD), im ÖNACE-Abschnitt C.

| Punkt | Festlegung |
| --- | --- |
| Berichtsmonat | Parameter; für die Abgabe 07/2026, Zeitraum 01.08.2025 bis 31.07.2026 |
| Tage | Kalendertage, an denen mindestens ein passender Zeitabschnitt besteht. Gleichzeitige Verhältnisse zählen einen Tag nur einmal; DV- und FD-Tage werden zusammengezählt. |
| Datenstand | Abweichend von Zählregel 4 der Fachbeschreibung gilt für jeden Tag die jüngste Lieferung, die diesen Tag enthält, verarbeitet nach den slebst festgelegten bzw. der Regeln der Fachabteilung. Die Liste ist eine Auswertung über den aktuellen Wissensstand, keine Monatsveröffentlichung. |
| Wirtschaftszweig | ÖNACE des jeweiligen Zeitabschnitts, so wie ihn die verwendete Lieferung ausweist: Lieferungen bis 12/2024 nach ÖNACE 2008, ab 01/2025 nach ÖNACE 2025. Gezählt wird Abschnitt C der jeweiligen Klassifikation. |
| Felder | PERSON_ID, GESCHLECHT, GEBURTSJAHR (unplausible Geburtsdaten: `Unbekannt`), TAGE |
| Format | CSV mit Semikolon, Datei `ministerium_JJJJ-MM.csv`, sortiert nach PERSON_ID, Vorlage in `vorlagen/` |
