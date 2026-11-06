# Web frontend – status and handoff (2026-11-06)

Read this file, then `web/README.md` (start commands), before working on `web/`. Repo-wide context: root `AGENTS.md`
→ `StateOfDevelopment.md`, `Problems.md`, `Phases.md`, `docs/PRD.md` (§1.1 medlyn pattern, §7 UI spec).

## 1 What it is

German web UI for StatAgent (KI Challenge 2026, Use Case 3), submission Fri 6 Nov 2026 09:00. Next.js 16 (App Router,
all pages client components) in medlyn styling, talking to the FastAPI backend (`statagent/api/`, started with
`.venv\Scripts\python.exe -m statagent web`, port 8000). The browser only talks same-origin: `next.config.ts` rewrites
`/api/*` → `http://127.0.0.1:8000/api/*` (override with env `STATAGENT_API`); `compress: false` so Server-Sent Events
stream unbuffered (verified: events arrive incrementally through the proxy).

Binding product rules (AGENTS.md) that the UI enforces:

- **No invented numbers.** Every number shown comes from an API response; missing data → abstention state
  („nicht vorhanden / nicht geliefert / mehrdeutig / nicht prüfbar“), 404 → „noch nicht verfügbar“, never a fallback
  value. Only client-side arithmetic: Δ columns (value − official, both from the API) and the reconciliation check
  „gelesen = gezählt + nicht gezählt + ausgeschlossen“ (✓/✗ from API metrics).
- **Quellennachweis everywhere:** chips under numbers/charts open a side panel with delivery file + SHA-256, run +
  checksum, rules + approver + time, classification version, SQL, example records „wie geliefert / wie gelesen“.
- **Approvals only by a named person (T7):** login = name in localStorage; the API rejects placeholder names (and any
  name containing "agent") with 422 – the UI shows that message. The UI never approves on its own.
- **German UI**, English code. Numbers formatted `de-DE` (392.236), see §5.

## 2 Run it

See `web/README.md`. Short version (Git Bash):

```bash
export PATH="/c/Users/pickm/tools/node22:$PATH"   # portable Node 22 – system Node 19 is too old
cd web && pnpm install && pnpm dev                 # http://localhost:3000 (backend must run on :8000)
pnpm build                                         # typecheck + production build, must pass
```

pnpm 10.34.8 is pinned via `packageManager` (corepack would otherwise fetch pnpm 12). Dependency age rule (only
releases older than 7 days) is enforced by `minimumReleaseAge: 10080` in `pnpm-workspace.yaml` + `.npmrc`; all
versions are exact in `package.json`. Do not add packages without that rule.

## 3 Pages (nav order) and what they use

| Page | Route | API | Notes |
| --- | --- | --- | --- |
| Übersicht | `/` | overview, statistik (all months) | KPI tiles, time series with DQ markers |
| Lieferungen | `/lieferungen` | lieferungen, profil, dateien, **SSE** pruefen | problem matrix (median-based highlight), file registry, integrity check |
| Läufe | `/laeufe` | laeufe, laeufe/{id}, **SSE** POST laeufe | start run (+ preview rules), live progress, history, detail drawer |
| Qualitätsberichte | `/qualitaetsberichte?monat=&regelwerk=&ansicht=` | qualitaetsberichte, …/{rs}/{m}, annahmen, rueckfragen | findings with filter, revisions side by side, Markdown QB (streamdown) |
| Klassifikationen | `/klassifikationen?klass=&code=&cv=` | klassifikationen, …/{klass}, …/{code}/erklaerung | browser, deterministic text, xyflow transition graph |
| Pensionen | `/pensionen?traeger=&jahr=` | pensionen, pensionen/zellen | Tab 12/13, break 2020, carrier tree + merger graph, cell evidence |
| Dashboard | `/dashboard` | statistik (many), statistik/monate, modelle | rule-set toggle, month select, ÖNACE 2008/2025 separate, pyramid, fluctuation, corridor overlay switch, pinned chat cards |
| Modelle | `/modelle` | modelle | banner, model cards (hashes, seeds, metrics per population), corridor per series, detector heatmap, synthetic runs, limits |
| Fragen | `/fragen` | fragen/vorschlaege, **SSE** POST fragen | see §4 |
| Exporte | `/exporte` | exporte, **SSE** exporte/aggregationen + ministerium, exporte/freigeben, exporte/datei | approve = human action (confirm dialog) |
| Agent | `/agent` | **SSE** POST agent (`probe`), agent/aufgaben, code, code/{id}, **SSE** code/{id}/ausfuehren | Probelauf switch (default off), proposals with diff + before/after |
| Freigaben | `/freigaben?regel=` | freigaben, regeln, regeln/{id}/entscheidung, code/{id}/entscheidung, veroeffentlichen | decision dialog with comment, 422 shown inline + toast |
| Protokoll | `/protokoll` | protokoll | change log + suggested commit message |

Strg+K (cmdk) jumps to pages, QB months and rules.

## 4 Fragen (chat) – behaviour

- POST `/api/fragen` body `{question, user, role, conversation_id, previous?, reading?, handling?, free_text?}`; events
  `status`, `clarification`, `card`, `text`, `abstention`, `done`, `error`. Example chips only FILL the input.
- **Chained Rückfragen:** a pick re-sends the same question in the same turn with
  `reading = {...clarification.answered, ...turn.reading, [term]: id}`; answered readings show as chips
  „n. Lesart „Wort“: Label ×“ – click = remove that key and re-send (the Rückfrage comes again).
- **Card** (`components/chat/answer-card.tsx`): claim-check badge „n Prüfungen · m Zahlen geprüft“ (hover = details),
  documented defaults, KPIs, chart (long bar labels → horizontal), table toggle, CSV export, pin to dashboard,
  evidence chips, deterministic explanation + graph for classification cards, link for QB cards, mean cards
  (`params.aggregate === "mean"`, `table.detail` = monthly values in a collapsible table).
- **Data-quality panel** (`components/chat/quality-panel.tsx`): per issue severity, description, three options
  (default = approved rule; unavailable ones disabled with reason), free text; „niedrig“ under „weitere Hinweise“.
  „Mit dieser Behandlung neu berechnen“ appends a NEW turn (official card stays visible) with `previous = card.params`,
  `reading = card.readings`, `handling` (non-default choices only), `free_text`. The recalculated card shows the
  warning banner, value / offiziell / Δ, official values as dashed/faint series, and the copy box (work.dq_copy,
  copy_id, n entfernt / n hinzugefügt, notes, hidden months, SQL – also in the Quellennachweis SQL tab).
- Verified 2026-11-05: Alter 08/2024 (DQ-05 ausschließen → 392.236 → 391.866), Bundesland 10/2025 (DQ-02 fortschreiben
  + DQ-08 free text → 313.154 → 390.664), Arbeiter 07/2026 (Rückfrage FD), Tirol 2025 (Rückfrage Jahr → mean 34.710).
- History lives in `sessionStorage` (per tab); pins in `localStorage` (`statagent-pins`).

## 5 Code map and conventions

- `app/globals.css`, `components/ui/*`, `components.json`, `hooks/use-mobile.ts`: copied **unchanged** from medlyn
  (`C:\Users\pickm\tools\ref\medlyn\apps\app`, CC BY-NC 4.0, see `NOTICE.md`). Put own CSS in `app/app.css`
  (imports globals.css; shiki dual theme, `.prose-stat` Markdown, xyflow tokens, stronger selected-toggle style).
- `components/shell/`: providers (theme, user, evidence, sidebar, toaster), sidebar, page header, cmdk, login, theme
  (medlyn-style inline script `lib/theme-script.ts`, class `dark`, key `statagent-theme`).
- `components/stat/`: `StatCard`, `StatChart` (line/bar/area/hbar/pyramid, markers, model band, flag dots, dashed
  reference series), `EvidenceProvider`/`useEvidence`/`EvidenceChips`/`ExampleRecordsView`, `ProgressCard`
  (SSE progress; `pct=null` = indeterminate), `CodeBlock`/`SqlBlock` (shiki, SQL+diff bundled offline), run parts
  (reconciliation, findings with filter, revisions), states (loading/empty/error/abstention), transition graph.
- `lib/api.ts` (`apiGet`, `apiPost`, `streamSse` POST-SSE parser, `ApiError` with German `detail`), `hooks/use-api.ts`,
  `use-sse-job.ts` (progress/result/error jobs), `use-stat.ts` (+ `pivot`), `use-markers.ts` (DQ months derived from
  `rules[].parameters.deliveries`, never hard-coded), `lib/format.ts` (`fmt`, `fmtMonth`, dates), `lib/types.ts`,
  `lib/models.ts` (Modelle contract).
- Pages must not `export` anything but the default component (Next.js rule). `useSearchParams` needs a `<Suspense>`.

## 6 Testing approach (no test suite in `web/`)

- `pnpm build` (typecheck) is the gate.
- Browser checks were done with headless Edge (`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`) driven
  by `puppeteer-core@23.11.1` installed in a **scratch folder outside the repo** (not a project dependency). Playwright
  MCP was not available. In Git Bash set `MSYS_NO_PATHCONV=1`, otherwise `/dashboard` becomes a Windows path.
- Safe test inputs (no real effects): Fragen questions, Agent with Probelauf ON, approval dialogs with an invalid name
  (e.g. „Testagent“ → 422). Never click approve/publish/export/run with a real name unless the team wants it.

## 7 Progress

| Area | Status |
| --- | --- |
| Shell, theme, login, cmdk, toasts, offline fonts | done |
| Übersicht, Lieferungen (+ SSE integrity check), Läufe (+ SSE run), Qualitätsberichte, Annahmen, Rückfragen | done, verified in browser |
| Klassifikationen (browser, explanation, graph), Pensionen (incl. cell evidence) | done, verified |
| Dashboard (+ corridor overlay, pinned cards), Modelle | done, verified |
| Fragen: StatCards, chained Rückfragen, data-quality panel + recalculation, mean cards | done, verified with the 4 test questions |
| Agent console with Probelauf, code proposals; Freigaben (rules, code with diff/SHA-256, publish) ; Protokoll; Exporte | done; real approvals/execution/exports deliberately not exercised |

## 8 Known problems and risks

| ID | Problem | Status / workaround |
| --- | --- | --- |
| W-01 | System Node is v19 (too old). | Always prepend `C:\Users\pickm\tools\node22` to PATH (README). |
| W-02 | `next dev` writes `web/AGENTS.md` (Next 16 agent rules) and re-adds it when deleted. | Harmless; commit it or leave it untracked. |
| W-03 | After editing shared modules (e.g. `navigation.ts`) the dev server sometimes served stale server modules → hydration mismatch on new routes. | Restart `pnpm dev`. Production build unaffected. |
| W-04 | Recharts line/bar animations restarted on re-render and never finished (only dots/axes visible). | **fixed 06.11.**: Recharts animations stay off; charts fade/rise in with CSS (`ENTER` in `stat-chart.tsx`, `motion-reduce` respected). |
| W-05 | Animated KPI counters show intermediate values for ~0.9 s (screenshots may catch e.g. 32.479 instead of 34.710). | By design (final value = API value, `aria-label` has the exact value); set reduced motion to skip. |
| W-06 | Corridor model is trained on values „wie geliefert“ (2025-06 shows the DQ-01 collapse), while the dashboard line uses approved rules. | Labelled in both places; don't compare them silently. |
| W-07 | Pinned dashboard cards are snapshots from pin time (incl. run/checksum), not refreshed. | **fixed 06.11.**: „Aktualisieren“ on each pinned card re-asks the same question with the same parameters/reading and replaces the snapshot (`updatePin`). |
| W-08 | Login is only a name in localStorage – no authentication; the API only rejects placeholder/agent names. | Acceptable for the challenge (T7 = named person + protocol); mention to the jury. |
| W-09 | Number format: spec said `de-AT`, but `de-AT` groups with a space (392 236); UI uses `de-DE` (392.236). | Intentional. |
| W-10 | `next-themes` stays a dependency only because the copied `components/ui/sonner.tsx` imports it; theme itself is medlyn's inline script. | Harmless; the Toaster gets the theme as a prop. |
| W-11 | Exporte „Freigeben“ uses `window.confirm` instead of a styled dialog. | **fixed 06.11.**: styled `Dialog` with file, SHA-256 and the approving name. |
| W-12 | Not exercised end-to-end: executing an approved code proposal, real rule/code approvals, publishing, Aggregations/ministry export, „Monat ausblenden“ (hidden-month gap), Rückfrage terms Menschen/Entwicklung/ÖNACE-Bruch, Modelle after the latest retrain. | Code paths exist; test with the team before the demo. |
| W-13 | Long questions over many months (e.g. a year with data-quality checks) take several seconds; the chat shows streamed status steps meanwhile. | Backend performance; nothing to do in the UI. |
| W-14 | Full-page screenshots in headless Edge show the sticky sidebar/header twice. | Screenshot artefact only. |

## 9 Next steps (if time)

- Exercise W-12 paths together with the team (with real names only when intended).
- Optional polish: styled confirm dialog on Exporte, mobile check of the Pensionen tables, `Monat ausblenden` demo.
- Keep `web/README.md`, this file and the root docs (Phases.md row „0 (web)“) in sync after changes.

## 10 Round „Verbesserungen“ (2026-11-05, late) – done in `web/`

- **Klassifikationen graph:** only the selected code's own transitions by default (switch „alle … Übergänge der Nachbarschaft
  zeigen“), wider columns, rows sorted by share, focus node highlighted, re-fit after layout (`components/stat/transition-graph.tsx`).
- **Pensionen:** sex toggle stays on top (drives the two time series); carrier + year moved into a sticky bar directly above
  „Pensionsart × Geschlecht“ and Tabelle 13. Year fallback: if the carrier has no data in the chosen year (e.g. SVB 2025),
  the nearest year with data is shown with a notice („… bestand nur bis 31.12.2019 – gezeigt wird 2019“); selects show
  carrier years and „(keine Daten)“.
- **Chat:** send button vertically centred; chart chosen per answer (time → line, long format month × category pivoted
  into one line per category, many categories → sorted horizontal bars, ≤ 8 parts → „Ring“ option) with a chart-type
  switcher; Rückfrage gets a free-text field „Anders gemeint?“ – mapped deterministically onto an offered reading by
  label keywords (shown as „nur Abgänge (aus „nur die Abgänge“)“), otherwise an honest hint (no guessing).
- **Errors lead to the fix:** `components/stat/fix-links.tsx` turns error/abstention texts into links (R-… → Freigaben,
  „Monatsläufe starten“ → Läufe, name/login hints, Klassifikationen, Agent). Used in ErrorState, AbstentionState,
  ProgressCard errors, chat errors, approval dialog.
- **Temporary approval („Probeweise anwenden“)** on every open rule in Freigaben (`components/stat/trial-apply.tsx`):
  POST `/api/laeufe` with `vorschau: [rule]` for a chosen month → the backend rolls the run back (no run row, no QB file,
  no approval, no protocol entry); shows offiziell vs. mit Regel (Probe) vs. Differenz. Verified with R-DQ03 / 2025-03
  (387.180 → 387.180, Z1 already counts duplicates once); latest stored run unchanged afterwards.

## 10b Changes 2026-11-06

- **Links between pages restored:** Lieferungen (month → QB, hash → Dateiregister, run → `/laeufe?lauf=`), Läufe opens the
  drawer from `?lauf=` and preselects `?monat=`, Lieferungen keeps `?monat` (highlight + scroll), `?ansicht`, `?q` in the URL,
  Quellennachweis panel links deliveries, runs, rules and closes on navigation (`EvLink`), Protokoll objects
  (`rule:` → Freigaben, `month:` → QB), QB header links run, delivery and rule IDs.
- **Data agent in Fragen:** badge „Agent · <tool>“ on the card (tooltip: arguments), „Verwendete Dateien“
  (`components/chat/sources-list.tsx`: files with role + SHA-256 + link to Dateiregister/QB, tables), abstention kinds
  „nicht verfügbar“ and „außerhalb des Datenbestands“ (no fix links for the latter), the chart kind chosen by the agent
  (e.g. donut) is kept, pension answers (years → no example records), sidebar shows „Agent: <model>“.
- **Deep link** `/fragen?frage=…` asks once (used for links and headless screenshots).
- Verified in headless Edge via the DevTools protocol (Node 22 WebSocket, no extra package).
- **Smoke test** `pnpm test:smoke` (`scripts/smoke.mjs`): 15 pages render without exceptions/console errors, expected text and
  links present; `--frage` asks one live question and waits for the card with claim check and „Verwendete Dateien“.
- Pensionen round (Problems.md SW-31): instant tooltips (`MarkerTipCtx` for chart markers, Radix tooltips for codes),
  series `title` → full names on hover, `SmallMultiples` with own axes, run chips as links, non-month run detail in Läufe,
  Agent page templates; StatChart markers accept `note`.
- Feedback round (Problems.md SW-30): Modelle detector scorecard, `ruleSetLabel` („Basis“/„Aufträge“) everywhere, ministry
  button gated on approved R-A3, chart switcher offers only sensible kinds (`toChart`, years count as time), curated
  suggestions, Codevorschläge explained on the Agent page, Fragen footer shows the logged person (`fragen_person`).
- Chart fade-in (W-04), approval dialog in Exporte (W-11), pin refresh (W-07); faulty-data options now also for Personen and
  Zu-/Abgänge (backend `quality.recompute`).

## 11 Open items that need the backend (not in `web/`)

| Wish | What is needed |
| --- | --- |
| ~~Check whether a question is feasible~~ | **done 06.11.**: „nicht verfügbar“ (missing fields) and „außerhalb des Datenbestands“ (history, physics, …) from the agent and the offline scope gate. |
| Rückfrage free text | every term has exactly 3 readings (done 06.11.); open: backend interpretation of the `reading` free text (today the UI maps keywords only). |
| Reports in the format of the original xlsx (Beispielbericht) | Generator for QB/statistics as xlsx in the layout of `beispielbericht_2024-08.xlsx` (backend `reporting/`), then the UI can list/download them under Exporte. |
| ~~More chart types driven by the question~~ | **done 06.11.**: the agent sends a chart wish (`apply_chart`), the UI keeps it when it fits. |

## 12 Requirements check (summary of a read-only review, 2026-11-05 late)

Technically almost complete; the gaps are mostly human steps (see root `docs/RUNBOOK.md`):
1. ~~Change orders 1–3 never executed for real~~ done 06.11. (agent task 14; sheet, QBs and ministry CSV in `abgabe/`).
2. ~~Ministry delivery missing~~ done: `abgabe/ministerium_2026-07.csv`, released 06.11. 07:30.
3. T8: met by `abgabe/protokoll/protokoll.md` (instruction, change, approver, time per entry); commits by the team.
4. ~~Open approvals R-DQ03/05/09 + `veroeffentlichen`~~ done 05./06.11. (basis series published, docs/RECOMPUTE.md).
5. Agent code path (T6) and live change never run end-to-end (W-12).
6. T4: no access to the Azure model received → agent runs with Anthropic `claude-sonnet-5-5`, switchable via `.env` (documented in abgabe/MODELLE.md).
7. ~~Docs partly stale~~ updated 06.11. (PRD marked historical, README final, calibration explained).
8. Final: commit + push to the submission repo before Fri 09:00.

## 13 Decisions on the reading rules (all approved by Mercy, 2026-11-05)

Official series (`stat_beschaeftigte`, Aggregations-Sheet, 24 QBs, ministry delivery) use exactly one approved handling per
problem (Fachbeschreibung §8 „Jede Annahme steht im Qualitätsbericht“, T7, area 5 „deterministisch“). Everything else stays
dynamic per user in the chat (data-quality panel, copy in `work.dq_copy`, „keine amtliche Zahl“).

| Rule | Decision | Reason (also given as `--kommentar`, stored in `ops.approval.comment` + protocol) |
| --- | --- | --- |
| R-DQ01 | approved 14:59 | Lieferung 2025-06 mit vertauschten Spalten BEGINN/ENDE: vertauscht gelesen; ohne Regel wären am Stichtag nur 21 statt rund 394.000 Verhältnisse aktiv, 2025-07 enthält dieselben Abschnitte richtig. |
| R-DQ07 | approved 15:45 | Veraltete ÖNACE-2003-Codes DA–DM (rund 50 Verhältnisse je Monat) dem Abschnitt C der gültigen ÖNACE zuordnen (Quellzuordnung). |
| R-DQ08 | approved 15:45 | Leere Merkmale (Bundesland, ÖNACE, Geschlecht, Qualifikation) der Ausprägung „unbekannt“ zuordnen statt Sätze zu verlieren (Quellzuordnung). |
| R-DQ03 | approved 23:19 | Exakt doppelte Sätze sind technische Doppellieferungen; jedes Verhältnis zählt einmal (Anhang A Regel 1), Kopien bleiben gespeichert und markiert. |
| R-DQ05 | approved 23:20 | Monat 13 ist ein falsches Datumsformat: Tag und Monat getauscht lesen, sonst Alter unbekannt; kein Verhältnis geht verloren. |
| R-DQ09 | approved 23:20 | Überlappende Abschnitte: der spätere Abschnitt gilt ab seinem Beginn (Fachbeschreibung §2); das Verhältnis zählt einmal. |
| R-DQ02, R-DQ04, R-DQ10 | not approved (deliberately) | Handled per statistic in the chat (three options + free text); QBs state „gezählt wie geliefert“ + Rückfragen RF-DQ02/RF-DQ04. |

Where the QBs get it from: `statagent/qa/report.py` lists every applied rule with `approved_by`, `approved_at`, `assumption`
and `justification` from `ops.rule`. The approval comment is stored in `ops.approval.comment` and in `abgabe/protokoll/protokoll.md`,
and is printed in the QB since 05.11. („Anmerkung bei der Freigabe (Name): …“, `statagent/qa/report.py`).

Approvals done (Mercy). Recalculation after the approvals of 23:19/23:20 (PowerShell, repo root), all steps needed, in this order:

```powershell
.venv\Scripts\python.exe -m statagent freigeben R-DQ03 --von "Vorname Nachname" --kommentar "Exakt doppelte Saetze = technische Doppellieferung; jedes Verhaeltnis zaehlt einmal (Anhang A Regel 1), Kopien bleiben markiert."
.venv\Scripts\python.exe -m statagent freigeben R-DQ05 --von "Vorname Nachname" --kommentar "Monat 13 = falsches Datumsformat; Tag/Monat getauscht lesen, sonst Alter unbekannt; kein Verhaeltnis geht verloren."
.venv\Scripts\python.exe -m statagent freigeben R-DQ09 --von "Vorname Nachname" --kommentar "Ueberlappung: spaeterer Abschnitt gilt ab seinem Beginn (Fachbeschreibung 2); Verhaeltnis zaehlt einmal."
.venv\Scripts\python.exe -m statagent bestand                     # store with R-DQ03/09, ~4 min
.venv\Scripts\python.exe -m statagent gesamtlauf                  # 24 runs + 24 QBs, ~14 min
.venv\Scripts\python.exe -m statagent kalibrierung                # totals match; 359 age cells differ (birth-year vs. swap, documented)
.venv\Scripts\python.exe -m statagent veroeffentlichen --von "Vorname Nachname" --regelwerk basis
.venv\Scripts\python.exe -m statagent aggregationen --regelwerk basis
.venv\Scripts\python.exe -m statagent protokoll                   # then one commit per approval with „Freigegeben-von: Name“ (T8)
```
