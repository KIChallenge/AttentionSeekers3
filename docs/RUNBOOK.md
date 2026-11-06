# Runbook – from the current state to the submission (and the jury demo)

All commands: `.venv\Scripts\python.exe -m statagent <Befehl>` (PowerShell) or `.venv/Scripts/python.exe -m statagent …` (bash). Web UI: see README „Weboberfläche“.
**Steps marked 👤 are human decisions (T7): only a named team member may do them – the tools never approve on their own.**

## 0 State (2026-11-06 03:00)

- §1 and §2 are **done**: R-DQ03/05/09 approved by Mercy (05.11. 23:19–23:20), store rebuilt, 24 runs (148–171) and 24 QBs, all 24 months **published (endgültig)**, `abgabe/aggregationen_basis.xlsx` + Open-Data-File regenerated, protocol exported, integrity and secret scan OK. What each step did and why: [RECOMPUTE.md](RECOMPUTE.md).
- Effect: 09/2024 = 393,453 (−1, R-DQ09); all other totals unchanged; calibration: totals + Tab1–Tab12 match, 359 age cells differ (R-DQ05 swap vs. the example report's year-based age).
- 06.11.: SW-07/10/19/27/28 done (recount on the copy for Personen and flows, calibration „bestanden – erklärt“, `sichern`/`wiederherstellen`, smoke test, chart motion/dialog/pin refresh).
- 06.11.: data agent live in „Fragen“ (Anthropic `claude-sonnet-5-5`, no Azure access received; switchable via `.env`), page links restored, test entries removed from the answer log (Problems.md §8).
- 06.11. 06:54–07:15: change orders 1–3 carried out by the agent (24 runs `auftraege`, sheet, 24 QBs, ministry CSV 32,741 persons).
- 07:30: `ministerium_2026-07.csv` released (Exporte), protocol exported.
- **Open:** commit + push; optional `veroeffentlichen --regelwerk auftraege`, `sichern`, rehearsal of a live change (Agent, Probelauf).

## 1 👤 Decide the open reading rules (Freigaben page or CLI)

Team decision (2026-11-05 evening): **approve R-DQ03, R-DQ05 (reworked) and R-DQ09**; R-DQ02, R-DQ04 and R-DQ10 stay unapproved – those
problems are handled per statistic in the chat (three options + free text, applied on a copy of the affected records, see README).

| Rule | Effect |
| --- | --- |
| R-DQ03 duplicates count once | counts unchanged (VVH are counted once anyway); copies shown as excluded in the reconciliation |
| R-DQ05 (reworked) month 13 = wrong date format, day and month swapped | flagged; read as JJJJ-TT-13 where TT ≤ 12 (08/2024: 143 of 370), else `fallback` (default „unbekannt“); parameter `exclude: true` would exclude all of them (shown as „nach Regel ausgeschlossen“). Totals unchanged; the age table no longer matches the example report (359 of 2,880 cells – the report used birth year only) |
| R-DQ09 overlaps: later segment wins | segment ends; 09/2024 −1 VVH (VVH 56000) |

The approval itself must be done by you under your name (the tools never approve, T7):

```powershell
.venv\Scripts\python.exe -m statagent regeln                     # list
.venv\Scripts\python.exe -m statagent freigeben R-DQ03 --von "Vorname Nachname"
.venv\Scripts\python.exe -m statagent freigeben R-DQ05 --von "Vorname Nachname" --kommentar "Monat 13 als falsches Format markieren, Tag/Monat tauschen"
.venv\Scripts\python.exe -m statagent freigeben R-DQ09 --von "Vorname Nachname"
```

## 2 Recompute the basis series (machine, ~20 min)

```powershell
.venv\Scripts\python.exe -m statagent bestand          # only if R-DQ03/09/10 were decided (store reading rules), ~4 min
.venv\Scripts\python.exe -m statagent gesamtlauf       # 24 runs, ~14 min → QBs
.venv\Scripts\python.exe -m statagent kalibrierung     # with the reworked R-DQ05: totals match, 359 age cells differ (documented)
```

👤 Publish (freeze) the basis series – „zuerst nach den bisherigen Regeln“:
```powershell
.venv\Scripts\python.exe -m statagent veroeffentlichen --von "Vorname Nachname" --regelwerk basis
.venv\Scripts\python.exe -m statagent aggregationen --regelwerk basis
```

## 3 👤 Change orders by language through our agents (UI „Agent“ or CLI)

Give each instruction as the team (it is logged with your name), e.g.:

```powershell
.venv\Scripts\python.exe -m statagent agent "Auftrag 1: Dienstvertrag und freier Dienstvertrag zusammen – Beschäftigungskategorie nur noch Arbeiter, Angestellte, Beamte, rückwirkend" --von "Vorname Nachname"
.venv\Scripts\python.exe -m statagent agent "Auftrag 2: Gezählt wird das ganze Monat statt dem Stichtag" --von "Vorname Nachname"
.venv\Scripts\python.exe -m statagent agent "Auftrag 3: Lieferung an das Ministerium für 07/2026, Arbeiter in Abschnitt C mit mindestens 200 Tagen" --von "Vorname Nachname"
```

Each creates a proposal (R-A1 / R-A2 / R-A3) with diff and before/after numbers (07/2026: categories 143,076 / 243,817 / 12,134; whole month 407,604 vs. 399,027 Stichtag; ministry 32,741 persons). Then:

1. 👤 `freigeben R-A1 --von …`, `freigeben R-A2 --von …`, `freigeben R-A3 --von …` (or Freigaben page)
2. `agent "Setze die freigegebenen Aufträge um" --von …` → classification rebuild (level Beschäftigungskategorie), 24 runs `auftraege` (~14 min), `abgabe/ministerium_2026-07.csv`
3. 👤 `lieferung-freigeben abgabe/ministerium_2026-07.csv --von …` (delivery approval with SHA-256)
4. `aggregationen --regelwerk auftraege` → `abgabe/aggregationen_auftraege.xlsx` (category sheet with Arbeiter/Angestellte/Beamte)
5. 👤 optionally `veroeffentlichen --von … --regelwerk auftraege`

## 4 👤 Protocol and commits (T8)

`protokoll` exports `abgabe/protokoll/protokoll.md` and prints the suggested message. One commit per change, message = instruction + `Freigegeben-von: Name`. The tools never commit.

## 5 Optional

- Language model: configured with Anthropic `claude-sonnet-5-5` (no Azure access received, ENV-10). To switch (e.g. to the operator's Azure endpoint) change `AGENT_PROVIDER`, `AGENT_API_KEY`, `AGENT_BASE_URL`, `AGENT_MODEL`, `AGENT_API_VERSION` in `.env` and restart `statagent web`; the sidebar shows the active model. Without a key the chat runs in the labelled offline mode.
- `modelle` (synthetic data + corridor + detector, ~10 min), `pensionen` (pension statistic, ~10 s).
- `geheimnisse` (secret scan) and `pruefen` (package integrity) right before the submission.

## 6 Rehearsal without traces

Agent console: switch on „Probelauf (wird zurückgerollt)“ (CLI: `agent "…" --probe`). The whole task runs – routing, proposal, diff, preview run with before/after – and is rolled back; generated files are removed. Use it to rehearse the live change before the jury; for the real demo switch it off.

## 7 Jury script (~15 min)

Before: API + web running (`statagent web`, `pnpm dev`), logged in as a named person (e.g. Mercy), browser zoom 100 %, `/fragen` cleared („Neues Gespräch“).

1. **Solution (2 min)** – Übersicht: 24 deliveries, 10,152,292 rows, every number with Quellennachweis. Lieferungen → click a month (opens its QB), a hash (Dateiregister) and a run number (Laufdetail); „Integrität prüfen“ → all SHA-256 unchanged.
2. **Errors found (3 min)** – Qualitätsberichte 2025-06 (DQ-01: 21 as delivered vs 394,252 read), 2025-10 (DQ-02: 77,510 missing VVH), 2025-03 (DQ-03 + DQ-04); real developments *erklärt – plausibel* (seasonality I/F/A, Tirol). Modelle: detector scorecard per error type (4/4 real errors, 0 false alarms), corridor flags 2025-03/06/10 – honest limits. Kalibrierung: 2,880 cells, „bestanden – Abweichungen vollständig durch R-DQ05 erklärt“.
3. **One assumption in detail (2 min)** – DQ-02 (Lieferung 2025-10 unvollständig): in Fragen „Abgänge im Oktober und November 2025“ → option „Aus 2025-09 fortschreiben“ → recalculated on a copy: Abgänge 10/2025 91,536 → 14,026 next to the official value; published numbers unchanged, QB 2025-11 shows the revision need. Alternative: DQ-16 phantom double registrations.
4. **Live change by language (4 min)** – Agent: type the jury's change (template „Sonderauswertung“ shows the form, e.g. „Erstelle eine Sonderauswertung: Arbeiter in Wien nach Altersgruppen“) → proposal (rule or code C-000N, readable file + SQL) → 👤 Freigaben: approve with name → Agent: „Setze die freigegebenen Aufträge um“ → before/after numbers → Protokoll shows instruction, change, approver. Changes of the counting rules run as their own rule set; published months never change.
5. **Data questions (4 min)** – Fragen (agent with Anthropic model, numbers only from SQL, claim check, „Verwendete Dateien“): „Zeitreihe der Beschäftigten nach Geschlecht“, „Wie viele Männer und Frauen waren im Juli 2026 beschäftigt?“ (ring), „Fluktuation je Wirtschaftszweig 2025“ (→ Rückfrage, three readings), „Fluktuationsrate nach Bundesland 2025“ (zoomed dots), „Was ist aus ÖNACE-Abschnitt J geworden?“ (transition graph), „Entwicklung der Alterspensionen von Männern und Frauen seit 2018“, „Wie viel verdienen Frauen in Tirol?“ (→ nicht verfügbar), „Wer war Napoleon?“ (→ außerhalb des Datenbestands). Open SQL and Quellennachweis (wie geliefert / wie gelesen) once.

Fallbacks: model unreachable → chat keeps working in the labelled offline mode; a page hangs → `pnpm dev` restart (W-03); the API restart cancels a running job (nothing is stored half).
