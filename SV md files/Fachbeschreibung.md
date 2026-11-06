# Fachbeschreibung Beschäftigungsstatistik

Stand: 21.10.2026 · gilt für die KI Challenge, Use Case StatAgent

## 1 Datenquelle

In der Zentralen Versicherungsdatei laufen alle Meldungen der Dienstgeber und sonstigen Stellen zusammen. Für die Beschäftigungsstatistik erhaltet ihr daraus monatlich eine Lieferung. Alle Daten sind synthetisch; die Größenordnung entspricht etwa einem Zehntel Österreichs.

## 2 Lieferungen

- 24 Lieferungen, `lieferung_2024-08.csv` bis `lieferung_2026-07.csv`, je eine pro Berichtsmonat.
- Jede Lieferung ist ein **Vollabzug**: Sie enthält alle Versicherungsverhältnisse, die in den letzten drei Monaten (Berichtsmonat und die zwei Vormonate) zumindest einen Tag bestanden haben.
- Meldungen können verspätet eintreffen oder später korrigiert werden. Eine spätere Lieferung kann daher für denselben Zeitraum andere Angaben enthalten als eine frühere.
- Format: CSV, Trennzeichen Semikolon, UTF-8, erste Zeile Spaltennamen. Alle Felder werden als Text geliefert.

| Feld | Inhalt |
| --- | --- |
| VVH_ID | ID des Versicherungsverhältnisses |
| PERSON_ID | pseudonymisierte ID der Person |
| GEBURTSDATUM | JJJJ-MM-TT |
| GESCHLECHT | siehe `geschlecht.csv` |
| BEGINN | Beginn des Zeitabschnitts, JJJJ-MM-TT |
| ENDE | Ende des Zeitabschnitts, JJJJ-MM-TT; leer = Verhältnis läuft |
| QUAL | Qualifikation, siehe `qualifikation.csv` |
| OENACE | Wirtschaftszweig (Abschnitt) des Dienstgebers |
| BUNDESLAND | Bundesland des Arbeitsortes, siehe `bundesland.csv` |

Ein Verhältnis kann aus mehreren Zeitabschnitten bestehen. Ändert sich ein Merkmal (Qualifikation, Bundesland oder Wirtschaftszweig), endet der Zeitabschnitt am Vortag und ein neuer beginnt; das Verhältnis und seine VVH_ID bleiben gleich. Die Zeitabschnitte eines Verhältnisses schließen lückenlos aneinander an. Eine Person kann mehrere Verhältnisse gleichzeitig haben.

## 2a Monatsbetrieb: jede Lieferung einzeln

Im Betrieb kommt jeden Monat genau eine Lieferung. Euer Ablauf bildet das nach:

- Ein Produktionslauf verarbeitet **genau eine Lieferung**, zum Beispiel `lauf --lieferung 2025-03`.
- Die Lieferungen werden **einzeln und in zeitlicher Reihenfolge** verarbeitet, von 2024-08 bis 2026-07.
- Ein Lauf darf nur die eigene Lieferung und frühere Lieferungen verwenden, nie spätere. Was im März 2025 veröffentlicht wird, darf nichts aus der Lieferung April 2025 wissen.
- Jeder Lauf erzeugt die Ergebnisse dieses Berichtsmonats: die Werte des Monats in der Datenbank, die Spalte des Monats im Aggregations-Sheet und den **Qualitätsbericht des Monats**.

Ein Gesamtlauf über alle Monate ist erlaubt, aber nur als Folge von 24 Einzelläufen.

## 3 Klassifikationen

| Datei | Inhalt |
| --- | --- |
| `oenace_2008.csv` | ÖNACE 2008, Abschnitte A–U |
| `oenace_2025.csv` | ÖNACE 2025, Abschnitte A–V |
| `bundesland.csv` | Bundesländer 1–9 |
| `qualifikation.csv` | Qualifikationen mit Beschäftigungskategorie und Kennzeichen freier Dienstvertrag |
| `geschlecht.csv` | Geschlecht |

Die Klassifikationen enthalten jeweils auch die Ausprägung „unbekannt“. Lieferungen bis einschließlich 12/2024 sind nach ÖNACE 2008 codiert, ab 01/2025 nach ÖNACE 2025.

## 4 Zählregeln

1. **Beschäftigte** sind Versicherungsverhältnisse, nicht Personen. Eine Person mit zwei Verhältnissen zählt zweimal.
2. **Stichtag** ist der Monatsletzte. Ein Verhältnis zählt im Berichtsmonat, wenn ein Zeitabschnitt am Stichtag besteht: Beginn ≤ Stichtag und Ende leer oder ≥ Stichtag.
3. **Merkmale** (Qualifikation, Wirtschaftszweig, Bundesland) werden aus dem Zeitabschnitt genommen, der am Stichtag besteht.
4. **Welche Lieferung gilt:** Jeder Berichtsmonat wird aus seiner eigenen Lieferung gerechnet (Lieferung 2025-03 für März 2025) und danach nicht mehr geändert. Weichen spätere Lieferungen für einen bereits veröffentlichten Monat ab, wird das im Qualitätsbericht als Revisionsbedarf ausgewiesen.
5. **Alter** in vollendeten Jahren am Stichtag.
6. **Beschäftigungskategorie** ist die Qualifikation laut `qualifikation.csv`: ArbeiterDV, AngestellteDV, Beamte, ArbeiterFD, AngestellteFD.
7. **Wirtschaftszweig** nach der Klassifikation, die im Berichtsmonat gilt: bis 12/2024 ÖNACE 2008, ab 01/2025 ÖNACE 2025.
8. Fehlende oder nicht zuordenbare Angaben behandelt ihr nach eigenen, begründeten Annahmen; oberste Regel ist, dass kein Verhältnis verloren geht. Jede Annahme steht im Qualitätsbericht. Rückfragen an die Fachabteilung sind möglich, aber nicht nötig.

## 5 Ergebnisse

**Aggregations-Sheet:** eine Excel-Datei mit je einem Blatt für Bundesland, Geschlecht, ÖNACE und Beschäftigungskategorie. Zeilen sind die Ausprägungen plus „Insgesamt“, Spalten die Berichtsmonate. ÖNACE steht wegen des Klassifikationswechsels in zwei Blättern: bis 12/2024 nach ÖNACE 2008, ab 01/2025 nach ÖNACE 2025. Die Summe jedes Blatts ergibt dieselbe Gesamtzahl. Bundesland mit Bezeichnung, ÖNACE mit Code; unbekannte Werte als eigene Zeile `Unbekannt`.

**Qualitätsbericht:** je Berichtsmonat ein eigener Bericht (24 Berichte) mit den Auffälligkeiten, die Rückfragen an die Fachabteilung und die ergriffenen Maßnahmen.

Die Zahlen liegen außerdem in eurer Datenbank (Datentabelle `stat_beschaeftigte`, siehe Aufgabenstellung, Anhang B); Datenanfragen der Jury werden von dort beantwortet. Vorlagen für alle Ergebnisse und für Rückfragen liegen im Ordner `vorlagen/`. Der `beispielbericht_2024-08.xlsx` zeigt die Monatstabellen für August 2024, gerechnet nach diesen Regeln.

## 6 Rückfragen an die Fachabteilung

Auffälligkeiten, die sich mit diesen Regeln nicht eindeutig lösen lassen, löst ihr mit eigenen plausiblen Annahmen oder klärt ihr mit der Fachabteilung. Eine Rückfrage braucht einen Beleg: betroffene Lieferung, Anzahl der Sätze und einige Beispiel-IDs. Die Antwort ist verbindlich und wird als Regel umgesetzt. Wichtig ist, dass ihr es dokumentiert.
