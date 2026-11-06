# StatAgent – Aufgabenstellung für die Teams

Oct 23, 2026 

## Worum es geht

In 24 Stunden baut ihr einen agentengestützten Statistikprozess. Er erstellt eine amtliche Beschäftigungsstatistik aus Einzeldaten sowie Statistiken aus aggregiert gelieferten Daten, sichert die Qualität und entwickelt sie weiter.

Die KI schreibt den Code und hilft bei der Interpretation. Gerechnet wird von Programmen, die lokal und auch ohne KI laufen können. Neben der Statistik baut ihr ebenso sorgfältig die Metainformationen auf, die sie verständlich machen: Klassifikationen, Beschreibungen, Definitionen.

Die Rollen eines Statistikteams – Klassifikation, Datenmanagement, Qualitätssicherung, Reporting – müssen abgedeckt sein. Wie ihr sie abbildet, zum Beispiel mit Agenten, Skills oder Workflows, bleibt euch überlassen. Vorwissen über die Sozialversicherung braucht ihr nicht.

## So entsteht eine Statistik

Jede Statistik durchläuft denselben Prozess, egal ob ihre Daten als Einzeldaten oder bereits aggregiert ankommen. Diesen Prozess baut ihr auf. Er ist hier vereinfacht dargestellt: In der Praxis laufen Schritte mehrfach, und geprüft wird an mehreren Stellen, nicht nur beim Einlesen.

&#91;embedded content: Prozess einer Statistik · von der Anlieferung bis zum Report\]

1. **Anlieferung.** Je nach Statistiktyp kommen die Daten als Einzeldaten (bei uns: die Beschäftigungsverhältnisse aus der Zentralen Versicherungsdatei) oder als fertig aggregierte Tabellen (bei uns: die Pensionsmeldungen der Pensionsversicherungsträger). Es ist sinnvoll, die Lieferungen unverändert als Rohdaten abzulegen, damit man später nachvollziehen kann, was geliefert wurde. Für die Challenge ist das nicht verlangt.
2. **Prüfen und bereinigen.** Die Daten werden auf Fehler geprüft und bereinigt. Wo das nicht geht, wird bei der liefernden Stelle eine Nachlieferung angefragt. Die bereinigten Daten werden in der Datenbank gespeichert, auch die Einzeldaten. Auf ihnen setzen alle weiteren Schritte auf.
3. **Anreichern.** Bei Bedarf kommen Logik oder Kennzahlen hinzu, etwa eine neue Zählregel, eine abgeleitete Gliederung oder eine Quote.
4. **Aggregieren und speichern.** Aus den bereinigten Einzeldaten werden die benötigten aggregierten Zahlen gebildet und in der Datentabelle der Statistik (`stat_`) gespeichert. Aggregiert angelieferte Daten gehen nach der Prüfung direkt dorthin.
5. **Ergebnisse prüfen.** Auch die aggregierten Zahlen werden geprüft, bevor sie hinausgehen: Passen die Summen, sind Sprünge in der Zeitreihe erklärbar, stimmen sie mit Vergleichswerten überein?
6. **Bereitstellen.** Aus den Datentabellen werden Reports, Lieferungen und Dashboards erzeugt. Fällt im Report noch etwas auf, geht es zurück in die Prüfung.

Dashboards direkt auf Einzeldaten gibt es in der Praxis für interne Zwecke; sie sind nicht Teil dieser Aufgabe.

### So ist eine Statistik aufgebaut

Eine Statistik ist im Grunde eine Datentabelle mit ihren Variablen, allen benötigten Dimensionen und den Metadaten dazu. Dafür gilt eine feste Konvention:

| Tabelle | Präfix | Inhalt |
| --- | --- | --- |
| Datentabelle | `stat_` | ein Wert je Zeile: Berichtszeitraum, eine Spalte je Dimension mit dem Code, Variable, Wert, Status, Datenstand; z. B. `stat_beschaeftigte` |
| Variablentabelle | eine für alle Statistiken | alle Variablen aller Statistiken, eine Zeile je Variable mit den Spalten Statistik, Variablencode, Variablenbezeichnung und Beschreibung |
| Klassifikationstabellen | `klass_` | die Dimensionen mit Codes, Bezeichnungen, Versionen, Gültigkeiten und Übergängen; z. B. `klass_geschlecht`, `klass_region`, `klass_oenace` |

Die Klassifikationstabellen gehören keiner einzelnen Statistik. Sie liegen um die Datentabellen herum, und jede Statistik verweist auf die, die sie braucht. Die Einzelheiten stehen in Anhang B.

## Eure Aufgabe in fünf Schritten

Euer StatAgent unterstützt das Statistikteam bei zwei Aufgaben:

1. **Eine neue Statistik anlegen und laufend verbessern.** Er liest die übermittelten Daten ein und prüft sie. Daraus ergibt sich, welche Variablen, Klassifikationen und welche Datentabelle die Statistik braucht; er prüft, was davon schon vorhanden ist, und legt Fehlendes an. Dann baut er das laufende Einlesen (ETL), legt die Ausgabeformate fest und definiert Qualitätsprüfungen und Regeln für das Einlesen. So wird die Statistik angelegt und befüllt. Prüfungen und Regeln wachsen laufend mit, weil mit jeder Lieferung neue Fehler auftauchen können.
2. **Sonderauswertungen und Fragen an die Daten.** Auf dem befüllten Bestand lassen sich Sonderauswertungen definieren und Fragen an die Daten stellen. Die Antworten kommen aus der Datenbank, nachvollziehbar mit Abfrage und Definition.

An der Beschäftigtenstatistik zeigt ihr das in fünf Schritten:

| Schritt | Zuständig | Womit | Ergebnis |
| --- | --- | --- | --- |
| 1 Daten einlesen und prüfen | Datenmanagement | 24 Lieferungen, lokale Datenbank | Datenmodell nach Vorgabe, versionierter Bestand |
| 2 Metadaten aufbauen | Klassifikation | geprüfte Daten, Klassifikationsdateien im Paket | Klassifikationen historisiert, je Begriff einmal, mit Übergängen |
| 3 Monatsbetrieb | Datenmanagement und Qualitätssicherung | eine Lieferung je Lauf | Ergebnis je Monat und Qualitätsbericht |
| 4 Ergebnisse bereitstellen | Reporting | Datenbank | Aggregations-Sheet, Antworten auf Datenanfragen |
| 5 Weiterentwickeln | alle, verteilt über eine Koordination | Änderungsaufträge, Pensionsmeldungen | drei Umstellungen, Ministeriums-Lieferung, neue Statistik |

### Schritt 1 – Daten einlesen und prüfen

Am Anfang stehen die Daten: Welche Merkmale und Codes kommen in den Lieferungen vor, und was passt nicht? Das Datenmanagement liest die Lieferungen ein und baut daraus nach der Vorgabe in Anhang B einen versionierten Bestand. Jede Lieferung enthält alle Zeiten der letzten drei Monate; Meldungen können verspätet kommen oder später korrigiert werden. Das Datenmanagement ist technisch für das Produktionsprogramm mit Datenmodell und Zählregeln verantwortlich.

### Schritt 2 – Metadaten aufbauen

Aus den eingelesenen und geprüften Daten ergibt sich, welche Variablen und Gliederungen die Statistik braucht. Die Klassifikation prüft, was davon schon vorhanden ist, und legt die übrigen an: Wirtschaftszweig, Region, Geschlecht, Alter, Qualifikation. Jede Klassifikation hat Versionen mit Gültigkeit und kennt die Übergänge zwischen ihnen, etwa von ÖNACE 2008 auf 2025. Die Klassifikation wird außerdem hinzugezogen, wenn neue Statistiken entstehen, unerklärbare Codes auftauchen oder eine Zeitreihe springt.

- **Mindestens:** die Klassifikationen in der Tiefe, die die Beschäftigtenstatistik braucht, je Begriff nur einmal.
- **Optimal:** ÖNACE bis zum 5-Steller und alle Gemeinden, Bezirke und Bundesländer seit 2011, mit allen Übergängen, abgeleitet aus den amtlichen Änderungslisten (Zusammenlegungen, Teilungen, Bezirksänderungen); euer System erklärt auf Nachfrage, was bei einem Übergang passiert ist.

### Schritt 3 – Monatsbetrieb

Im Betrieb kommt jeden Monat genau eine Lieferung, und euer System bildet das nach:

- Ein Produktionslauf verarbeitet genau eine Lieferung, zum Beispiel `lauf --lieferung 2025-03`, in zeitlicher Reihenfolge von 2024-08 bis 2026-07. Ein Lauf verwendet nur die eigene und frühere Lieferungen.
- Die Qualitätssicherung findet Datenfehler, unterscheidet sie von echten Entwicklungen und trifft begründete Annahmen nach den fachlichen Regeln in Anhang A. Jeder neu gefundene Fehler wird als Prüfung oder Einleseregel festgehalten, damit ihn der nächste Lauf von selbst erkennt.
- Jeder Lauf erzeugt das Ergebnis des Berichtsmonats und einen eigenen Qualitätsbericht. Veröffentlichte Monate werden nicht mehr geändert; liefert eine spätere Lieferung andere Angaben, steht der Revisionsbedarf im Qualitätsbericht.

### Schritt 4 – Ergebnisse bereitstellen

Das Reporting erzeugt das Aggregations-Sheet nach Bundesland, Geschlecht, ÖNACE und Beschäftigungskategorie und beantwortet Fragen zu den Daten. Antworten kommen aus der Datenbank, mit sichtbarer Abfrage und genannter Definition; bei Mehrdeutigkeit fragt euer System zurück.

### Schritt 5 – Weiterentwickeln

Zuerst erstellt ihr die Statistik nach den Regeln der Fachbeschreibung. Danach setzen eure Agenten drei Änderungsaufträge um, die in `aenderungsauftraege.md` beschrieben sind:

| Nr. | Auftrag | Kurz | Geht an |
| --- | --- | --- | --- |
| 1 | Dienstvertrag und freier Dienstvertrag zusammen | Beschäftigungskategorie nur noch Arbeiter, Angestellte, Beamte, rückwirkend | Klassifikation, dann Reporting |
| 2 | Ganzes Monat statt Stichtag | gezählt wird jedes Verhältnis, das mindestens einen Tag im Monat besteht | Datenmanagement |
| 3 | Lieferung an das Ministerium (Sonderauswertung) | Personen mit mindestens 200 Tagen als Arbeiter im Abschnitt C in den letzten zwölf Monaten | Reporting |

Die Aufträge kommen an einer Stelle an, bei einem Koordinator-Agenten oder einem Teammitglied, und werden an die zuständige Rolle verteilt. Danach laufen die Monate wieder einzeln durch. Wer weiterkommt, liest zusätzlich die aggregierten Pensionsmeldungen der Pensionsversicherungsträger ein und baut daraus eine neue Statistik der Pensionen. Jeder Träger liefert die Zahlen zu den Tabellen 12 und 13 der Jahresergebnisse (Pensionsstand und vorzeitige Alterspensionen, 2018–2025) in seinem eigenen Excel-Format; die Summen über alle Träger bildet ihr selbst. Zum 1.1.2020 wurden Träger zusammengelegt, auch das muss eure Klassifikation der Träger abbilden. Vorsicht bei den Unterteilungen innerhalb eines Trägers: Sie gehen auf frühere, eigenständige Träger zurück, die zusammengelegt und als Versicherungsbereiche weitergeführt werden. „Arbeiter“ und „Angestellte“ der PVA sind die früheren Pensionsversicherungsanstalten der Arbeiter und der Angestellten, nicht die Qualifikation der Beschäftigtenstatistik; sie gehören in die Gliederung der Versicherungsträger, nicht in die Qualifikation. Dabei durchläuft der StatAgent dasselbe Vorgehen wie oben: vorhandene Variablen und Klassifikationen prüfen, fehlende anlegen, Einlesen, Prüfungen und Ausgabe festlegen.

## Technische Regeln

1. **Die KI schreibt Code, das Programm rechnet.** Zahlen kommen in die Datenbank ausschließlich durch Code, der auch ohne Sprachmodell läuft. Zwei Läufe mit denselben Daten und Regeln liefern dieselben Zahlen.
2. **Lokal und offline.** Produktionsprogramm und Datenbank laufen auf eurem eigenen Gerät, ohne Internet und ohne Cloud-Dienst, und lassen sich händisch per Kommandozeile oder WebUI starten.
3. **Regeln als Daten.** Regeln und Zuordnungen liegen in der Datenbank, nicht als versteckte Konstanten im Code. Code und Regeln müssen für Menschen lesbar sein.
4. **Modelle.** Für die Agenten verwendet ihr die bereitgestellten Modelle am Azure-Endpunkt. Das Modell muss austauschbar sein.
5. **Eure Agenten setzen um, nicht euer Entwicklungswerkzeug.** Claude Code, Codex, Cursor und Ähnliches dürft ihr verwenden, um das System zu bauen. Umstellungen im Betrieb und Lieferungen führen aber eure eigenen Agenten auf Anweisung in Sprache durch.
6. **Eure Agenten dürfen im Betrieb Code schreiben und ausführen, unter fünf Bedingungen.** Der Code (a) liegt als lesbare, dokumentierte Datei vor, (b) lässt sich von Menschen per Kommandozeile oder WebUI starten, (c) läuft ohne Sprachmodell und rechnet reproduzierbar, (d) ist vor der ersten Ausführung freigegeben und (e) wird mit Anweisung und Ergebnis protokolliert. Ob euer Agent bei Unbekanntem gleich Code erzeugt oder zuerst zurückfragt, entscheidet ihr.
7. **Mensch gibt frei.** Jede Änderung an Regeln oder Code und jede Lieferung gibt ein Teammitglied frei. Nachweisbar ist das im Protokoll mit dem Namen der freigebenden Person, dem Zeitpunkt und dem, was freigegeben wurde (Datei, Regel oder Lieferung). Ein Platzhalter wie „Team“ reicht nicht.
8. **Protokoll.** Jede Änderung über eure Agenten bleibt nachvollziehbar: Anweisung, was geändert wurde, wer freigegeben hat. Ein Git-Commit je Änderung reicht, mit der Anweisung als Nachricht und einer Zeile „Freigegeben-von: Name“.

Die fachlichen Regeln zum Umgang mit fehlerhaften Daten stehen in Anhang A.

Praktische Hinweise zur Umgebung (Versionen, lange Läufe, große Tabellen) stehen im `README.md` des Pakets.

## Abgabe und Fachjury

Abgabe ist am Freitag um 9 Uhr für:

- [ ] Aggregations-Sheet nach Bundesland, Geschlecht, ÖNACE und Beschäftigungskategorie für alle Monate, nach den alten Regeln und nach den Änderungsaufträgen
- [ ] 24 Qualitätsberichte: gefundene Fehler, getroffene Annahmen mit Begründung, Zuordnungen, Revisionsbedarf
- [ ] Ministeriums-Lieferung für den Berichtsmonat 07/2026
- [ ] Protokoll aller Änderungen über eure Agenten
- [ ] kurze Angabe zu den verwendeten Modellen

Bei der Fachjury habt ihr etwa 15 Minuten:

1. **Präsentation:** eure Lösung, die gefundenen Fehler, eine Annahme im Detail.
2. **Live-Änderung:** Die Jury gibt eine kleine, unbekannte Änderung vor. Ihr setzt sie per Sprache über eure Agenten um und zeigt Protokoll und Zahlen vorher und nachher.
3. **Datenanfragen:** Die Jury fragt zum Beispiel nach einer Zeitreihe, nach Männern und Frauen oder nach der Fluktuation je Wirtschaftsbereich.

## Bewertung

Die ersten fünf Bereiche folgen den fünf Schritten, der sechste bewertet die Bedienbarkeit. Alle sechs zählen gleich, je 20 von 120 Punkten. Die Mindestanforderungen zusammen ergeben eine vollständige Beschäftigtenstatistik; für das Optimum braucht ihr auch die Zusatzdaten.

| Bereich | Mindestanforderung | Optimum | Punkte |
| --- | --- | --- | --- |
| 1 Datenmanagement | liest alle Lieferungen korrekt ein, Datenmodell nach Vorgabe | versionierter Bestand über alle Lieferungen, Pensionsmeldungen aller Träger trotz unterschiedlicher Formate eingelesen | 20 |
| 2 Klassifikation | legt die benötigten Klassifikationen an, je Begriff nur einmal | ÖNACE bis zum 5-Steller und Regionen Österreichs vollständig historisiert, Übergänge aus den amtlichen Änderungslisten, kennt und erklärt sie | 20 |
| 3 Qualitätssicherung | erkennt einen Teil der Fehler, Qualitätsbericht je Monat | erkennt alle Fehler, unterscheidet sie von echten Entwicklungen, jede Annahme begründet und dokumentiert | 20 |
| 4 Reporting | Aggregations-Sheet nach den Regeln der Fachbeschreibung | Datenanfragen (können sich auch auf Klassifikationen und Metadaten beziehen) richtig beantwortet, Dashboard | 20 |
| 5 Weiterentwicklung und Betrieb | Produktion läuft deterministisch | alle Änderungsaufträge und Ministeriums-Lieferung umgesetzt, nachvollziehbar protokolliert, Live-Änderung per Sprache gelingt | 20 |
| 6 Bedienbarkeit | alles lässt sich über die Konsole steuern: Läufe starten, Ergebnisse und Qualitätsberichte ansehen, Änderungen freigeben | übersichtliche Weboberfläche für Läufe, Qualitätsberichte und Annahmen, Klassifikationen, Freigaben und Fragen an die Daten | 20 |

Eigene Annahmen sind ausdrücklich erlaubt. Punkte gibt es, wenn sie begründet, dokumentiert und fachlich vertretbar sind. Wer Verhältnisse verliert oder eine echte Entwicklung als Fehler „korrigiert“, verliert Punkte.

## Anhang A – Fachliche Regeln für Beschäftigtenstatistik

1. **Kein Verhältnis geht verloren.** Das ist die oberste Regel. Kommt ein Satz in einer Lieferung mehrfach vor, wird das Verhältnis trotzdem nur einmal gezählt.
2. **Annahmen begründen und dokumentieren.** Bei Fehlern in den Daten trefft ihr selbst begründete Annahmen und haltet fest, wie ihr jeden betroffenen Satz zugeordnet habt.
3. **Rückfragen sind möglich, aber nicht nötig.** Die Fachabteilung vor Ort beantwortet Fragen, wenn ihr einen Beleg mitbringt: betroffene Lieferung, Anzahl der Sätze, einige Beispiel-IDs.

Die Zählregeln selbst stehen in der Fachbeschreibung im Paket.

## Anhang B – Vorgabe für das Datenmodell

Jede Statistik besteht aus einer Datentabelle mit dem Präfix `stat_`; ihre Variablen stehen in der gemeinsamen Variablentabelle. In der Datentabelle steht ein Wert je Zeile, mit einer Spalte je Dimension; was gemessen wird, steht als Variable in einer eigenen Spalte, der Wert daneben (Long-Format). Die Dimensionen verweisen auf Klassifikationstabellen mit dem Präfix `klass_`. Davon gibt es je Begriff nur eine, egal in wie vielen Statistiken sie vorkommt.

| Tabelle | Inhalt |
| --- | --- |
| **Je Statistik** |  |
| `stat_<statistik>` | Datentabelle: Berichtszeitraum (Art: Stichtag, Monat, Jahr; von–bis), eine Spalte je Dimension mit dem Code, Variable, Wert, Status (vorläufig, endgültig, gesperrt), Datenstand bzw. Lieferung |
| Beschreibung | Name, Quelle, Statistiktyp (Einzeldaten oder aggregiert geliefert), welche Dimensionen mit welcher Klassifikation und Ebene, Anmerkungen und Fußnoten |
| **Gemeinsam für alle Statistiken** |  |
| Variablentabelle | eine Tabelle für alle Variablen aller Statistiken, je Zeile: Statistik, Variablencode, Variablenbezeichnung, Beschreibung (Definition, Einheit, Berechnungslogik); der Variablencode ist das, was in der Spalte Variable der stat\_-Tabelle steht |
| `klass_<begriff>` | Klassifikation, z. B. `klass_geschlecht`, `klass_region`, `klass_oenace`: Codes mit Bezeichnung, Ebene, übergeordnetem Code und Gültigkeit von–bis, Versionen wie ÖNACE 2008 und 2025 |
| Übergänge | Code alt → Code neu zwischen zwei Versionen oder Ständen, mit Beziehungstyp 1:1, 1:n, n:1 oder m:n und Gültigkeitsdatum |
| Quellzuordnung | wie eine Lieferung ein Merkmal schreibt (z. B. „W“, „2“, „Frauen“) und auf welchen Code das führt – statt einer zweiten Klassifikation |

Ausschnitt aus `stat_beschaeftigte`:

```csv
zeitraum_art;zeitraum_von;zeitraum_bis;region;oenace;geschlecht;qualifikation;alter;variable;wert;status;stand
Stichtag;2025-03-31;2025-03-31;6;C;W;ArbeiterDV;45;Beschaeftigungsverhaeltnisse;3;endgueltig;Lieferung 2025-03
```

Eine Statistik aus den Pensionsmeldungen mit anderen Dimensionen, aber derselben `klass_geschlecht`:

```csv
zeitraum_art;zeitraum_von;zeitraum_bis;versicherungstraeger;pensionsart;geschlecht;variable;wert;status;stand
Jahresdurchschnitt;2025-01-01;2025-12-31;PVA-ARB;ALTER;M;Pensionen;395763;endgueltig;Meldung PVA 2025
```

Eine neue Statistik bekommt eine eigene `stat_`-Tabelle und eine Beschreibung, trägt ihre Variablen in die Variablentabelle ein und verwendet die vorhandenen `klass_`-Tabellen.

## Anhang C – Unterlagen

Alle Unterlagen gibt es zu Beginn.

| Bestandteil | Inhalt |
| --- | --- |
| Monatslieferungen | 24 Lieferungen 08/2024 bis 07/2026 aus der Zentralen Versicherungsdatei, synthetisch, etwa ein Zehntel Österreichs; jede Lieferung ein Vollabzug mit allen Zeiten der letzten drei Monate |
| Datenbank | lokale PostgreSQL per Docker-Compose, lädt alle Lieferungen beim ersten Start; alle Felder zunächst als Text |
| Fachbeschreibung | Satzaufbau, Zählregeln, Monatsbetrieb, Ergebnisformate |
| Änderungsaufträge | die drei Aufträge aus Schritt 5 im Detail |
| Beispielbericht | Monatsbericht 08/2024 im Layout des Dachverbands, zum Eichen eures Ablaufs |
| Vorlagen | für Aggregations-Sheet, Ministeriums-Lieferung, Qualitätsbericht und Rückfrage |
| Pensionsmeldungen | Ordner pensionen/: Meldungen der Pensionsversicherungsträger zu Tabelle 12 (Pensionsstand) und 13 (vorzeitige Alterspensionen) der Jahresergebnisse, 2018–2025, je Träger und Jahr eine Excel-Datei in trägereigenem Format |
| LLM-Zugang | Azure-Endpunkt mit vorgegebenen Modellen |
| Fachabteilung | Fachexperten vor Ort für Rückfragen |

**Klassifikationen**

| Klassifikation | Im Paket | Inhalt | Quelle |
| --- | --- | --- | --- |
| Grundausstattung | `klassifikationen/` | ÖNACE 2008 und 2025 (Abschnitte), Bundesland, Qualifikation, Geschlecht | Fachabteilung |
| ÖNACE 2003, 2008 und 2025 | `klassifikationen/oenace/` | alle Ebenen bis zum 5-Steller in mehreren Ausgabeformen, dazu die Umsteiger 2003 → 2008 und 2008 → 2025 | Statistik Austria |
| Gemeinden | `klassifikationen/regionen/gemeinden_JJJJ-01-01.csv` | 16 Stände von 01.01.2011 bis 01.01.2026: Gemeindecode, Name, politischer Bezirk und Bundesland | [Gliederung Österreichs in Gemeinden](https://data.statistik.gv.at/web/meta.jsp?dataset=OGDEXT_GEM_1) |
| Politische Bezirke | `klassifikationen/regionen/bezirke_JJJJ-01-01.csv` | 16 Stände: Bezirkscode, Name, Bundesland | [Gliederung Österreichs in Politische Bezirke](https://data.statistik.gv.at/web/meta.jsp?dataset=OGDEXT_POLBEZ_1) |
| Bundesländer | `klassifikationen/regionen/bundeslaender.csv` | Code und Name | Statistik Austria |
| Änderungen der Gliederung | `klassifikationen/regionen/Änderungen/` | amtliche Änderungslisten: Änderungen der Gemeindekennziffern seit 2002 mit Zusammenlegungen, Teilungen und Bezirkszusammenlegungen (ODS), jährliche Änderungen der Verwaltungsgliederung 2002–2027 und Gemeindeänderungen seit 1945 (PDF) | Statistik Austria |
| Hintergrund | – | Beschreibung der regionalen Gliederungen | [Regionale Gliederungen bei Statistik Austria](https://www.statistik.at/services/tools/regionale-internationale-daten/regionale-daten-und-gliederungen/regionale-gliederungen) |

Die regionalen Daten stehen unter der Lizenz CC BY 4.0 (Quelle: Statistik Austria).
