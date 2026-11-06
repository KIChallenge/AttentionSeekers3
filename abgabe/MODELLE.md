# Verwendete Modelle – StatAgent (Kurzangabe zur Abgabe)

**Kein Modell rechnet eine amtliche Zahl.** Alle Werte in `stat_beschaeftigte`, `stat_pensionen`, den Aggregations-Sheets, Qualitätsberichten und der Ministeriums-Lieferung entstehen ausschließlich durch deterministisches SQL/Python (Technische Regel T1). Zwei Arten von Modellen kommen vor:

## 1 Sprachmodell für die Agenten (austauschbar)

| Punkt | Stand |
| --- | --- |
| Anbieter / Zugang | Die Aufgabenstellung sieht die bereitgestellten Modelle am Azure-Endpunkt vor (T4). **Zugriff auf das Azure-Modell wurde nicht erhalten** – es wurden weder Endpunkt noch Schlüssel bereitgestellt (ENV-10). Entwickelt und getestet wurde deshalb mit **Anthropic `claude-sonnet-5-5`** (OpenAI-kompatibler Endpunkt, Funktionsaufrufe). |
| Austauschbarkeit | Das Modell kann **jederzeit ohne Codeänderung gewechselt** werden: nur `.env` anpassen und `statagent web` neu starten – `AGENT_API_KEY`, `AGENT_MODEL`, optional `AGENT_PROVIDER` (openai, anthropic, azure, gemini, compatible), `AGENT_BASE_URL`, `AGENT_API_VERSION`. Für Azure: `AGENT_PROVIDER=azure`, `AGENT_BASE_URL=<Endpunkt>`, `AGENT_MODEL=<Deployment>`, `AGENT_API_VERSION=…` (die alten `AZURE_OPENAI_*` gelten weiter). So kann der Betreiber das Modell an die eigene Infrastruktur anpassen. |
| Ohne Modell | Fehlt der Schlüssel oder ist das Modell nicht erreichbar, laufen Agenten und Chat im gekennzeichneten **Offline-Modus** weiter: eine deterministische Absichtserkennung (`statagent/agents/intent.py`) wählt Werkzeug und Parameter und lehnt Fragen außerhalb des Datenbestands ab. Produktion und Datenbank hängen nie vom Modell ab (T2). |
| Übertragene Daten | an den Anbieter gehen nur der Fragetext, die Werkzeugbeschreibungen und die Parameter der vorherigen Frage – keine Datensätze aus der Datenbank |
| Aufgabe des Modells | nur Auswahl: Absicht, zuständige Rolle, Werkzeug, Parameter (Monate, Gliederung, Lesart). **Es nennt nie Zahlen**; Texte werden aus Abfrageergebnissen in festen Vorlagen erzeugt; der Claim-Check (`statagent/reporting/claims.py`) prüft jede Zahl gegen das Abfrageergebnis, bevor sie angezeigt wird. |
| Protokoll | jeder Aufruf in `ops.llm_call` (Deployment, Modell, Zweck, Tokens, Dauer); jede Antwort in `ops.answer` (Frage, Lesart, Werkzeugaufrufe, Ergebnis-Hash, Claim-Check, Modell) |
| Code durch Agenten (T6) | Sonderauswertungen werden aus einer geprüften Vorlage mit Parametern erzeugt (lesbare Datei in `statagent/generated/`, läuft ohne Sprachmodell, nur nach Freigabe der exakten SHA-256 durch eine Person) |

Beim Bau des Systems wurde zusätzlich das Entwicklungswerkzeug Claude Code (Anthropic) verwendet; es hat keine Regel freigegeben, keine Änderung im Betrieb umgesetzt und keine Lieferung erzeugt (T5, T7).

## 2 Eigene Modelle: Erwartungskorridor und Fehlerdetektor (Phase 3b)

Wie bei medlyn: eigene synthetische Daten erzeugen, darauf trainieren, getrennt auf zurückgehaltenen synthetischen **und** auf den echten Lieferungen bewerten, Grenzen offen nennen. Modelle **markieren und schlagen vor**; sie korrigieren keine Daten und schreiben nie in `stat_*` (Ausgaben: `ops.model`, `synth.*`, Seite „Modelle“ mit Banner „Modell – keine amtliche Zahl“).

| Punkt | Inhalt |
| --- | --- |
| Synthetische Lieferungen | `statagent/ml/synth.py`: Mikrosimulation von Versicherungsverhältnissen, kalibriert an den realen Läufen (Zu-/Abgangsraten je ÖNACE-Abschnitt und Kalendermonat, eigene Raten für Saisonregionen Tirol/Salzburg/Vorarlberg/Kärnten, Jahr-zu-Jahr-Schwankung der Raten, Qualifikationsmix, Hintergrundprobleme wie Monat 13, ÖNACE-2003-Codes, leere Codes, Doppelmeldungen, Nachmeldungen); je Lauf 36 Lieferungen im gelieferten Spaltenformat; **eingepflanzte, gelabelte Fehler** DQ-01 (Spalten vertauscht), DQ-02 (unvollständige Lieferung), DQ-03 (Duplikate), DQ-04 (fehlende freie Dienstverträge) mit zufälligem Monat und Ausmaß |
| Reproduzierbarkeit | fester Seed je Lauf → gleiche Prüfsumme (Seed 1 zweimal erzeugt: identisch); Kalibrierungs-Hash, Daten-Hash und Modell-Hash in `ops.model` |
| Populationen | Training Seeds 1–8 · Kalibrierung 9–16 · Test 17–20 (je 36 synthetische Lieferungen, Maßstab 1:10) · **getrennt davon** die 24 echten Lieferungen mit den Labels aus Problems.md §2.1 |
| Fehlerdetektor | je Fehlerart eine standardisierte logistische Regression (scikit-learn 1.7.2, `random_state` fest) auf Lieferungsmerkmalen (Anteil leerer BEGINN, ENDE < BEGINN, Duplikatanteil, FD-Anteil und -Verhältnis zum Vormonat, Zeilen- und Bestandsverhältnis, Wiederfinden der Vormonats-VVH, Monat-13-Anteil, Anteil leerer Codes); Ausgabe: Wahrscheinlichkeit + die Merkmale, die sie treiben |
| Erwartungskorridor | je Reihe (Insgesamt, Abschnitte A/C/F/I, Tirol, freie Dienstverträge; Werte „wie geliefert“) Vorhersage der Monatsveränderung durch den Median des Kalendermonats aus den synthetischen Trainingsjahren, Band aus konformen Quantilen der Kalibrierungsresiduen (Soll-Abdeckung 99 %); außerhalb = Verdacht auf Datenfehler, ein bleibender Niveausprung (z. B. ÖNACE-Umstellung) wird nach einem Monat übernommen |

### Ergebnisse (Stand des letzten Trainings, `python -m statagent modelle`)

Modelle `ops.model` 7 (Detektor) und 8 (Korridor), trainiert 05.11.2026 19:29, Seed 20261105, synthetischer Lauf 68 (Training: 8 Läufe, Seeds 1–8 · Kalibrierung: 8 Läufe, Seeds 9–16 · Test: 4 Läufe, Seeds 17–20). Daten-Hash `c94e4cb468a0e18e…`, Modell-Hash Detektor `b3b2c7a7ab190950…`, Korridor `cf1915fe483ebac5…`.

**Fehlerdetektor** – je Population getrennt:

| Fehlerart | synthetischer Test: TP / FP / FN | Präzision / Recall | echte 24 Lieferungen: TP / FP / FN | Präzision / Recall |
| --- | --- | --- | --- | --- |
| DQ-01 | 5 / 0 / 0 (von 5 eingepflanzt, n = 144) | 1,00 / 1,00 | 1 / 0 / 0 (n = 24) | 1,00 / 1,00 |
| DQ-02 | 7 / 0 / 0 (von 7 eingepflanzt, n = 144) | 1,00 / 1,00 | 1 / 0 / 0 (n = 24) | 1,00 / 1,00 |
| DQ-03 | 8 / 0 / 0 (von 8 eingepflanzt, n = 144) | 1,00 / 1,00 | 1 / 0 / 0 (n = 24) | 1,00 / 1,00 |
| DQ-04 | 6 / 0 / 0 (von 6 eingepflanzt, n = 144) | 1,00 / 1,00 | 1 / 0 / 0 (n = 24) | 1,00 / 1,00 |

Markierte echte Lieferungen: 2025-03 DQ-03 (Wahrscheinlichkeit 0,998); 2025-03 DQ-04 (Wahrscheinlichkeit 0,996); 2025-06 DQ-01 (Wahrscheinlichkeit 0,996); 2025-10 DQ-02 (Wahrscheinlichkeit 0,981). Höchste Wahrscheinlichkeit aller übrigen Lieferung × Fehlerart-Kombinationen: 0,008.

**Erwartungskorridor**:

- synthetischer Test: Abdeckung **99,3 %** bei Soll 99 % (672 saubere Monatswerte); eingepflanzte Fehler außerhalb des Korridors: DQ-02 7/7, DQ-04 6/6
- echte Lieferungen (Werte wie geliefert), außerhalb des Korridors: total 2025-03, total 2025-06, total 2025-10, A 2025-06, A 2025-10, C 2025-01, C 2025-06, C 2025-10, F 2025-06, F 2025-10, I 2025-06, I 2025-10, Tirol 2025-06, Tirol 2025-10, FD 2025-03, FD 2025-06, FD 2025-10.
  Alle Markierungen fallen auf bekannte Lieferfehler (03/2025 DQ-04, 06/2025 DQ-01 wie geliefert, 10/2025 DQ-02) oder den ÖNACE-Umstieg 01/2025 im Abschnitt C (DQ-13/RD-03); **keine Markierung** in den Saisonreihen Beherbergung/Gastronomie (I), Bau (F), Land- und Forstwirtschaft (A) und Tirol außerhalb dieser Monate.

### Grenzen (ehrlich)

- Die Saisonmuster der synthetischen Daten sind aus denselben 24 realen Lieferungen kalibriert, auf denen bewertet wird – die Bewertung auf den echten Daten ist für die Saisonalität **nicht unabhängig**.
- Je Fehlerart gibt es in den echten Daten **nur eine** betroffene Lieferung: Präzision/Recall auf den echten Daten beruhen auf 24 Fällen und sagen wenig über neue Fehlerarten.
- Nur vier Fehlerarten werden gezielt eingepflanzt; andere Fehler (z. B. DQ-16-Doppelmeldungen) erkennt der Detektor nicht – dafür gibt es die regelbasierten Prüfungen in jedem Monatslauf.
- Maßstab 1:10: relative Zufallsschwankungen der synthetischen Reihen sind größer als in den echten Daten.
- Der Korridor arbeitet auf Werten „wie geliefert“; Monate mit bekannten Lieferfehlern (2025-03, 2025-06, 2025-10) fallen daher erwartungsgemäß heraus.
