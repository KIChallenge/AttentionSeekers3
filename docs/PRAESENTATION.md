# Präsentationsskript – StatAgent (Fachjury, ca. 15 Minuten)

Ablauf laut Aufgabenstellung: **1 Präsentation** (Lösung, gefundene Fehler, eine Annahme im Detail) · **2 Live-Änderung** per Sprache über die Agenten · **3 Datenanfragen** der Jury. Danach: **Fragen-Katalog** mit Antworten (Teil 4), besonders zu den Modellen.

**Vorbereitung (5 Minuten vorher):** API und Web laufen (`.venv\Scripts\python.exe -m statagent web`, `cd web; pnpm dev`) · im Browser http://localhost:3000, angemeldet als **Mercy** (oder Test User) · in „Fragen“ „Neues Gespräch“ · Zoom 100 % · Tabs vorbereitet: Übersicht, Qualitätsberichte, Modelle, Fragen, Agent, Freigaben, Protokoll.

---

## 1 Präsentation (7 Minuten)

### 1.1 Die Lösung in einem Satz (1 Minute) – Seite „Übersicht“

> „StatAgent macht aus 24 Monatslieferungen mit 10.152.292 Sätzen die amtliche Beschäftigtenstatistik – **das Programm rechnet, die KI rechnet nie**. Jede Zahl hat einen Quellennachweis bis zur gelieferten Datei, jede Änderung eine Freigabe durch eine Person, und alles läuft lokal ohne Cloud.“

Drei Grundsätze nennen:
1. **Deterministisch:** gleiche Daten + gleiche Regeln = gleiche Zahlen; jeder Lauf speichert eine Prüfsumme.
2. **Nichts geht verloren, nichts wird geändert:** alle 115 Paketdateien unverändert geladen (SHA-256), fehlerhafte Sätze bleiben in jeder Statistik; behandelt wird nur beim Lesen über freigegebene Regeln.
3. **Agenten schlagen vor, Menschen geben frei:** Regeln, Code und Lieferungen werden erst wirksam, wenn eine namentlich genannte Person freigibt.

Klick: **Lieferungen** → einen Monat anklicken (öffnet den Qualitätsbericht), eine Prüfsumme (Dateiregister), eine Laufnummer (Laufdetail). „Integrität prüfen“ → alle SHA-256 unverändert.

### 1.2 Gefundene Fehler (3 Minuten) – Seite „Qualitätsberichte“

> „Wir haben 17 Datenfehler gefunden und von 6 echten Entwicklungen unterschieden, die man gerade **nicht** korrigieren darf.“

Die vier großen zeigen:
| Lieferung | Fehler | Wie gefunden / was gemacht |
| --- | --- | --- |
| 06/2025 | **DQ-01** BEGINN und ENDE vertauscht | wie geliefert wären nur **21** Verhältnisse aktiv statt **394.252** → Leseregel R-DQ01 liest die Spalten getauscht |
| 10/2025 | **DQ-02** Lieferung unvollständig | **77.510** Verhältnisse fehlen, gleichmäßig über alle Merkmale → Wert wie geliefert, im QB ausgewiesen, Fortschreibung als Option im Chat |
| 03/2025 | **DQ-03** exakte Duplikate · **DQ-04** alle freien Dienstverträge fehlen | Duplikate zählen einmal (R-DQ03), FD-Lücke ausgewiesen |
| jede Lieferung | DQ-05 Geburtsmonat 13, DQ-07 alte ÖNACE-2003-Codes, DQ-08 leere Codes, DQ-16 Doppelmeldungen | je eigene Leseregel bzw. Kennzeichnung |

Echte Entwicklungen zeigen (Einstufung „erklärt – plausibel“): Saison in Beherbergung/Gastronomie, Bau, Landwirtschaft, Tirol; ÖNACE-Umstellung 01/2025; Rückgang der Beamten.

Klick: **Modelle** → „Fehlerdetektor: Trefferbilanz“ (4 von 4 echten Fehlern, 0 Fehlalarme) → über eine rote Zelle fahren (z. B. 10/2025 DQ-02: nur 80 % der Vormonats-Verhältnisse wieder geliefert, −20,5 % Sätze).

> „Die Modelle sind ein zweites Paar Augen – sie markieren, entscheiden aber nichts. Gezählt und korrigiert wird nur über Regeln.“

Kalibrierung erwähnen: **alle 2.880 Zellen** des Beispielberichts nachgerechnet – „bestanden, Abweichungen vollständig durch R-DQ05 erklärt“ (359 Alterszellen, weil wir Geburtsmonat 13 mit vertauschtem Tag/Monat lesen; mit der Lesart des Beispielberichts stimmen alle 2.880).

### 1.3 Eine Annahme im Detail (2 Minuten) – DQ-02, Seite „Fragen“

Frage stellen: **„Abgänge im Oktober und November 2025“**

> „In 10/2025 fehlen 77.510 Verhältnisse. Offiziell bleibt der Wert wie geliefert – wir erfinden keine Daten. Aber wer eine Statistik braucht, sieht das Problem direkt an der Zahl und kann wählen.“

Im Kasten „Datenqualität“ bei DQ-02 **„Aus 2025-09 fortschreiben“** wählen → „Mit dieser Behandlung neu berechnen“:
- Abgänge 10/2025: **91.536 → 14.026**, Zugänge 11/2025: **88.155 → 14.901**
- gerechnet auf einer **Kopie** der betroffenen Sätze, daneben der offizielle Wert; veröffentlichte Zahlen bleiben unverändert; der Qualitätsbericht 11/2025 weist den Revisionsbedarf aus.

> „Begründung der Annahme: die Lücke ist gleichmäßig verteilt und verschwindet in 11/2025 wieder – ein Lieferfehler, keine echte Abgangswelle. Trotzdem ist das keine amtliche Zahl, deshalb nur als Option mit Kennzeichnung.“

---

## 2 Live-Änderung per Sprache (4 Minuten) – Seite „Agent“

Ablauf (genau so zeigen, auch wenn die Jury etwas anderes vorgibt):
1. Die Änderung der Jury **wörtlich** ins Feld tippen (Beispiel: „Erstelle eine Sonderauswertung: Arbeiter in Wien nach Altersgruppen“). Probelauf aus.
2. Der Agent ordnet zu (Koordination → Rolle), legt einen **Vorschlag** an: Regel (R-…) oder Code (C-000N, lesbare Datei + SQL), mit Vorher/Nachher-Zahlen. **Noch nichts ist wirksam.**
3. **Freigaben** → Vorschlag prüfen → mit Namen freigeben (eine Person, kein Agent – T7).
4. **Agent** → „Freigegebene Aufträge umsetzen“ (Vorlage-Knopf) → Läufe/Ausführung mit Fortschritt, Vorher/Nachher.
5. **Protokoll** → neuer Eintrag: Anweisung, was geändert wurde, wer freigegeben hat, wann.

> „Neue Zählregeln laufen als eigenes Regelwerk – veröffentlichte Monate bleiben eingefroren. So haben wir auch die drei Änderungsaufträge umgesetzt: 24 Monate ‚Aufträge‘, ein eigenes Aggregations-Sheet und die Ministeriums-Lieferung.“

Falls die Änderung eine bestehende Regel betrifft (z. B. „Zähle Personen statt Verhältnisse“): zeigen, dass der Agent den passenden Werkzeugweg wählt oder ehrlich „nicht umsetzbar ohne Rückfrage“ sagt – nie raten.

---

## 3 Datenanfragen (4 Minuten) – Seite „Fragen“

> „Ein Sprachmodell versteht die Frage und wählt Werkzeug und Parameter. Die Zahl kommt aus SQL, der Text aus einer Vorlage, und ein Claim-Check prüft jede Zahl gegen das Abfrageergebnis, bevor sie angezeigt wird.“

Erprobte Fragen (alle als Vorlage in der Leiste):
| Frage | Was man sieht |
| --- | --- |
| Zeitreihe der Beschäftigten nach Geschlecht | 2 Linien, 24 Monate, Markierungen der Lieferfehler |
| Wie viele Männer und Frauen waren im Juli 2026 beschäftigt? | Ring + Kennzahlen, „Verwendete Dateien“ |
| Fluktuation je Wirtschaftszweig 2025 | **Rückfrage** mit drei Lesarten (mehrdeutiger Begriff) |
| Fluktuationsrate nach Bundesland 2025 | Punktdiagramm mit gezoomter Achse (kleine Unterschiede) |
| Was ist aus ÖNACE-Abschnitt J geworden? | Übergangsgraph 2008 → 2025 |
| Entwicklung der Alterspensionen von Männern und Frauen seit 2018 | Pensionsstatistik, 2 Linien |
| Wie viel verdienen Frauen in Tirol? | **„nicht verfügbar“** – Einkommen nicht geliefert, dazu was verfügbar ist |
| Wer war Napoleon? | **„außerhalb des Datenbestands“** – keine Antwort |

Bei einer Antwort einmal öffnen: **SQL** und **Quellennachweis** (Lieferung + SHA-256, Lauf + Prüfsumme, Regeln + Freigebende, Beispielsätze „wie geliefert“ vs. „wie gelesen“).

---

## 4 Fragen-Katalog mit Antworten

### 4.1 Modelle – Sprachmodell (Agent)

**Welches Sprachmodell verwendet ihr?**
Anthropic `claude-sonnet-5-5` über einen OpenAI-kompatiblen Endpunkt mit Funktionsaufrufen. Laut Aufgabe waren Azure-Modelle vorgesehen; **Zugriff darauf haben wir nicht erhalten** (weder Endpunkt noch Schlüssel). Dokumentiert in `abgabe/MODELLE.md`.

**Wie austauschbar ist das Modell (T4)?**
Nur über `.env`: `AGENT_PROVIDER` (openai, anthropic, azure, gemini, compatible), `AGENT_API_KEY`, `AGENT_MODEL`, `AGENT_BASE_URL`, `AGENT_API_VERSION` – API neu starten, fertig, keine Codeänderung. Für Azure: Provider `azure`, Endpunkt als Base-URL, Deployment als Modell. Der Anbieter wird sogar am Schlüssel erkannt.

**Was genau macht das Modell – und was nicht?**
Es **wählt nur aus**: eines von sieben Werkzeugen (Beschäftigtenstatistik, Pensionen, Code erklären, Qualitätsbericht, Definition, „nicht im Datenbestand“, „außerhalb des Datenbestands“) und dessen Parameter (Monate, Gliederung, Filter, Diagrammart). Es nennt **nie eine Zahl** und schreibt nie in die Statistik. Die Zahl kommt aus deterministischem SQL, der Text aus einer festen Vorlage.

**Wie verhindert ihr Halluzinationen?**
Drei Schichten: (1) das Modell darf keine Zahlen ausgeben, nur Werkzeug + Parameter, die wie jede Eingabe gegen Whitelists validiert werden; (2) Texte entstehen aus Vorlagen mit den Abfragewerten; (3) der **Claim-Check** findet jede Zahl im Text und prüft sie gegen das Abfrageergebnis – passt eine nicht, wird der Text nicht angezeigt (fail closed). Zusätzlich lehnt ein deterministischer Filter Fragen ohne Bezug zu den Daten ab, auch wenn das Modell anders entscheiden würde.

**Was passiert ohne Modell oder ohne Internet?**
Alles läuft weiter: Produktion, Läufe, Berichte, Exporte brauchen nie ein Modell (T2). Der Chat wechselt in den gekennzeichneten **Offline-Modus** – ein deterministischer deutscher Parser versteht die dokumentierten Fragetypen und fragt sonst zurück.

**Welche Daten gehen an den Anbieter?**
Nur der Fragetext, die Werkzeugbeschreibungen und die Parameter der vorherigen Frage – **keine Datensätze**. Der Schlüssel liegt nur in `.env` (nicht im Repo; ein Secret-Scan prüft Dateien und Git-Historie).

**Wie nachvollziehbar sind Modellaufrufe?**
Jeder Aufruf steht in `ops.llm_call` (Modell, Zweck, Tokens, Dauer – im Schnitt ca. 2 Sekunden), jede Antwort in `ops.answer` (Frage, Lesart, Werkzeugaufruf, Ergebnis-Hash, Claim-Check, Modell, Person). In der Antwortkarte steht „Agent · Werkzeug“ mit den gewählten Parametern.

**Schreibt der Agent Code (T6)?**
Ja, aber kontrolliert: aus einer geprüften Vorlage mit Parametern als lesbare Python-Datei, die **ohne Sprachmodell** reproduzierbar rechnet. Ausgeführt wird sie erst, wenn eine Person genau diese Fassung (SHA-256) freigegeben hat; Anweisung und Ergebnis kommen ins Protokoll.

**Habt ihr beim Bau KI verwendet?**
Ja, das Entwicklungswerkzeug Claude Code. Es hat das System gebaut, aber **keine Regel freigegeben, keine Änderung im Betrieb umgesetzt und keine Lieferung erzeugt** – die Änderungsaufträge haben wir selbst in Sprache an unsere eigenen Agenten gegeben (T5).

### 4.2 Modelle – eigene Modelle (Erwartungskorridor, Fehlerdetektor)

**Welche eigenen Modelle gibt es und wozu?**
Zwei, beide nur zum **Markieren**: ein **Fehlerdetektor** (welche Lieferung hat welchen Fehler?) und ein **Erwartungskorridor** (liegt ein Monatswert außerhalb des Erwartbaren?). Sie schreiben nie in `stat_*` und korrigieren keine Daten; die Seite trägt das Banner „Modell – keine amtliche Zahl“.

**Worauf habt ihr trainiert – es gibt doch nur 24 Lieferungen?**
Genau deshalb auf **synthetischen Daten**: ein eigener Generator (`statagent/ml/synth.py`) simuliert Versicherungsverhältnisse, kalibriert an unseren echten Läufen (Zu-/Abgangsraten je ÖNACE-Abschnitt und Kalendermonat, Saisonregionen, Qualifikationsmix, Hintergrundprobleme wie Monat 13 oder alte Codes). Darin pflanzen wir **gelabelte Fehler** ein: DQ-01 Spalten vertauscht, DQ-02 unvollständige Lieferung, DQ-03 Duplikate, DQ-04 fehlende freie Dienstverträge – mit zufälligem Monat und Ausmaß.

**Wie habt ihr getrennt und bewertet?**
Training: Seeds 1–8 · Kalibrierung: Seeds 9–16 · **Test: Seeds 17–20, beim Training zurückgehalten** – das Modell hat sie nie gesehen. Getrennt davon die **24 echten Lieferungen** mit den Labels aus unserer Fehleranalyse. Je 36 synthetische Lieferungen pro Lauf, Maßstab 1:10.

**Wie funktioniert der Fehlerdetektor?**
Je Fehlerart eine **standardisierte logistische Regression** (scikit-learn, fester `random_state`) auf zehn Lieferungsmerkmalen: Anteil leerer BEGINN, ENDE vor BEGINN, Duplikatanteil, Anteil freier Dienstverträge und Verhältnis zum Vormonat, Zeilen- und Bestandsverhältnis zum Vormonat, Anteil der Vormonats-Verhältnisse, die wieder geliefert werden, Monat-13-Anteil, Anteil leerer Codes. Ausgabe: Wahrscheinlichkeit + die Merkmale, die sie treiben (Tooltip auf der Seite).

**Warum logistische Regression und kein neuronales Netz?**
Wenig, klar strukturierte Merkmale; jede Entscheidung muss erklärbar sein (Merkmale im Tooltip); kleine echte Stichprobe; reproduzierbar mit festem Seed. Ein komplexeres Modell würde hier nichts besser machen, aber die Nachvollziehbarkeit verschlechtern.

**Wie gut ist der Detektor?**
Synthetischer Test: DQ-01 5/5, DQ-02 7/7, DQ-03 8/8, DQ-04 6/6 gefunden, **0 Fehlalarme** (144 Lieferungen). Echte Lieferungen: alle 4 Fehler gefunden (06/2025 DQ-01, 10/2025 DQ-02, 03/2025 DQ-03 und DQ-04, Wahrscheinlichkeiten 0,98–1,00), **0 Fehlalarme**; die höchste Wahrscheinlichkeit aller übrigen Kombinationen war 0,008.

**Wie funktioniert der Erwartungskorridor?**
Je Reihe (Insgesamt, ÖNACE A/C/F/I, Tirol, freie Dienstverträge) sagt er die Monatsveränderung über den Median des Kalendermonats aus den synthetischen Trainingsjahren vorher; das Band kommt aus **konformen Quantilen** der Kalibrierungsresiduen mit Soll-Abdeckung 99 %. Ergebnis im synthetischen Test: **99,3 %** Abdeckung (672 saubere Werte); eingepflanzte Fehler DQ-02 7/7 und DQ-04 6/6 außerhalb. Auf den echten Daten fallen alle Markierungen auf bekannte Lieferfehler (03/2025, 06/2025, 10/2025) oder den ÖNACE-Umstieg 01/2025 – **keine Markierung** in den Saisonreihen außerhalb dieser Monate.

**Wo sind die Grenzen?** (ehrlich, steht in `abgabe/MODELLE.md`)
- Je Fehlerart gibt es in den echten Daten nur **eine** betroffene Lieferung – 100 % auf 24 Fällen ist wenig aussagekräftig für neue Fehlerarten.
- Die Saisonmuster der Synthese sind aus denselben 24 Lieferungen kalibriert, auf denen bewertet wird – für die Saisonalität nicht unabhängig.
- Nur vier Fehlerarten werden eingepflanzt; andere (z. B. Doppelmeldungen DQ-16) erkennen die regelbasierten Prüfungen in jedem Monatslauf, nicht das Modell.
- Der Korridor arbeitet auf Werten „wie geliefert“, deshalb fallen die Fehlermonate erwartungsgemäß heraus.

**Sind die Modelle reproduzierbar?**
Ja: fester Seed (20261105) und Seeds je Population; Daten-, Kalibrierungs- und Modell-Hash in `ops.model`; derselbe Seed erzeugt dieselben Daten (geprüft). Neu trainieren: `python -m statagent modelle` (ca. 10 Minuten).

### 4.3 Datenmanagement und Klassifikation

**Wie stellt ihr sicher, dass kein Verhältnis verloren geht?**
Jeder Monatslauf bricht ab, wenn ein am Stichtag aktives Verhältnis nicht genau einmal gezählt wird; je Monat wird abgerechnet: gelesen = gezählt + nicht gezählt + ausgeschlossen. Nicht zuordenbare Codes landen in einem sichtbaren Code „nicht zuordenbar“, nie im Nichts.

**Was heißt „versionierter Bestand“?**
`store.segment` hält jede gelieferte Zeile mit Lieferung, Problemkennzeichen und angewendeten Regeln; jede spätere Lieferung kann frühere Monate ändern, das zeigt der Revisionsbedarf im Qualitätsbericht – veröffentlichte Monate bleiben unverändert.

**Klassifikationen?**
Alle Begriffe je einmal (`klass_*`): ÖNACE 2003/2008/2025 bis zur Unterklasse (5.027 Codes), Regionen 2011–2026 historisiert (2.965 Stände), über 3.300 Übergänge aus den amtlichen Änderungslisten (Gemeindezusammenlegungen, Umsteiger ÖNACE). Jeder gelieferte Code (40,6 Mio. Werte) löst sich in genau einen gültigen Code auf. Die Seite „Klassifikationen“ erklärt jeden Code mit Übergangsgraph.

**Pensionen?**
28 Meldungen von sieben Trägern (PVA, SVA, SVB, VAEB, VAN bis 2019; ab 2020 SVS und BVAEB) in sechs Formatfamilien (inkl. Formatwechsel, Zahlen als Text, Fusionen 2020: SVA + SVB + VAN → SVS, VAEB → BVAEB), alle eingelesen, 378 Summenprüfungen ohne Abweichung; jede Zahl bis zur gelieferten Zelle nachvollziehbar.

### 4.4 Qualitätssicherung und Annahmen

**Woran unterscheidet ihr Fehler von echten Entwicklungen?**
Fehler sind lieferungsbezogen und verschwinden in der nächsten Lieferung oder widersprechen der Logik (ENDE vor BEGINN, Monat 13). Echte Entwicklungen sind wiederkehrend (Saison), schrittweise oder durch Klassifikation/Gesetz erklärt (ÖNACE-Umstellung, Gesetzesänderungen bei Schwerarbeitspensionen) – Einstufung „erklärt – plausibel“, nichts wird korrigiert.

**Welche Regeln sind freigegeben, welche nicht – und warum?**
Freigegeben (Mercy): R-DQ01 (Spalten 06/2025 getauscht lesen), R-DQ03 (Duplikate einmal), R-DQ05 (Monat 13 = Tag/Monat getauscht), R-DQ07/08 (alte und leere Codes zuordnen), R-DQ09 (Überlappungen). **Bewusst nicht** freigegeben: R-DQ02, R-DQ04, R-DQ10 – dort würden wir Daten ergänzen; stattdessen wird das Problem an der Zahl angezeigt und im Chat als Option auf einer Kopie angeboten.

**Warum nicht nicht erklärbare Auffälligkeiten (z. B. Altershäufung bei 74)?**
Belegt untersucht, nicht korrigiert: es ist der älteste Jahrgang (kaum jemand vor 1949), die Häufung wandert mit der Zeit mit – das spricht für eine abgeschnittene Altersgrenze in den Lieferungen, lässt sich aber nicht beweisen. Deshalb „nicht erklärbar“, mit Beleg im Qualitätsbericht.

### 4.5 Änderungsaufträge und Betrieb

**Wie wurden die drei Änderungsaufträge umgesetzt?**
In Sprache an unsere Agenten gegeben (Aufgaben 10–12) → Regeln R-A1/2/3 vorgeschlagen → freigegeben → „Setze die freigegebenen Aufträge um“: Klassifikationsebene Arbeiter/Angestellte/Beamte, **24 Monate Regelwerk „Aufträge“** (ganzes Monat statt Stichtag; 07/2026: **407.604** statt 399.027), eigenes Aggregations-Sheet und 24 Qualitätsberichte, **Ministeriums-Lieferung** mit **32.741 Personen** (≥ 200 Tage Arbeiter in ÖNACE C, je Tag die jüngste Lieferung), freigegeben. Alles im Protokoll.

**Was passiert, wenn ein langer Lauf abbricht?**
Jeder fertige Monat wird sofort gespeichert; ein erneutes „Umsetzen“ macht beim nächsten offenen Monat weiter. Ein abgebrochener Einzellauf wird komplett zurückgerollt – es gibt nie halbe Ergebnisse.

**Läuft das auch auf einem anderen Rechner?**
Ja: frischer Clone + Datenbank neu aufbauen (ca. 30 Minuten) oder eine Sicherung einspielen (`sichern` / `wiederherstellen`, 0,5 GB statt 10 GB, mit SHA-256). Freigaben wandern über `abgabe/protokoll/freigaben.json` mit und werden nur für unveränderte Regeln wiederhergestellt.

### 4.6 Bedienbarkeit

**Was kann man über die Konsole und was über das Web?**
Alles über beide: Läufe starten, Qualitätsberichte und Annahmen ansehen, Klassifikationen erklären, Regeln, Code und Lieferungen freigeben, Fragen an die Daten, Exporte. Das Web zeigt zu jeder Zahl den Quellennachweis; Konsole: `python -m statagent <Befehl>` mit deutschen Befehlsnamen.

**Wie sicher ist die Freigabe?**
Für die Challenge ist die Anmeldung ein Name (kein Passwort) – bewusst einfach, dokumentiert. Platzhalter wie „Team“, „Agent“, „Test“ werden abgelehnt; die erlaubten Personen stehen in `.env`. Für den Produktivbetrieb bräuchte es Single Sign-on und Rollen.

---

## 5 Notfälle während der Präsentation

| Problem | Reaktion |
| --- | --- |
| Modell antwortet nicht | „Genau dafür gibt es den Offline-Modus“ – die Frage läuft deterministisch weiter |
| Seite hängt | `pnpm dev` neu starten; Daten sind in der Datenbank, nichts geht verloren |
| Agent-Vorschlag passt nicht | Vorschlag ablehnen (Freigaben → Ablehnen) – zeigt, dass nichts ohne Person wirksam wird |
| Frage außerhalb der Daten | Das ist ein Feature: „außerhalb des Datenbestands“ bzw. „nicht verfügbar“ |
