# AGENTS.md – StatAgent (KI Challenge 2026, Use Case 3)

Read first: `StateOfDevelopment.md` (state, architecture, tech stack, rules/scoring), `Problems.md` (all data/package issues with IDs DQ-/PEN-/KL-/ENV-/SPEC-/RD-), `Phases.md` (plan + progress table §1.1, UI styling §1.2). Task documents: `SV md files/`. Game plan for the remaining build: `docs/PRD.md`. Prior art and licences: `docs/references.md`. Web frontend (`web/`): `web/STATUS.md` (handoff: pages, API use, conventions, progress, known problems W-01…) + `web/README.md` (start commands).

## Ground rules (agreed with the team)

- **Never edit, rename or delete delivered data or package files** (`lieferungen/`, `klassifikationen/`, `pensionen/`, `vorlagen/`, `datenbank/`, `beispielbericht_2024-08.xlsx`, `SV md files/`). Data errors are part of the challenge: list them in `Problems.md`, keep faulty records in every statistic/graph, handle them only via reading rules at read time.
- **Rules are approved only by a named human** (`freigeben … --von "Name"`). Agents/dev tools must never approve rules or deliveries themselves (T7).
- **Do not commit or push** – the team commits itself (one commit per change, message + `Freigegeben-von: Name`).
- Numbers come only from deterministic SQL/Python, never from an LLM (T1). Local and offline (T2).
- Docs are in English, domain terms in German. Keep the three project docs compact and in sync; update the progress table in `Phases.md` after each step.
- New dependencies: only releases older than 7 days (`pip install --uploaded-prior-to <date>`), then `pip freeze > requirements.txt`.

## Product principles (team decision 2026-11-05)

- **Language:** source and backend in English – Python identifiers, modules, comments, logs, our own DB schemas `ops` (operations) and `store` (versioned store) and our raw helper tables in `roh`. Prescribed names stay German: the Anhang-B model in `public` (`stat_*`, `klass_*`, `variable`, `quellzuordnung`, `statistik_beschreibung`, …) and the delivered `roh.lieferung` / `klassifikation.*`. Everything a user sees is German: web UI, CLI command names, help and output, reports, rule texts, explanations. Domain terms (VVH, ÖNACE, Bundesland, Lieferung, Stichtag) stay German in everything users see; in code they get English names (`delivery`, `reference_date`), except the delivered field names, which are kept as identifiers (`vvh_id`, `person_id`, `qual`, `oenace`, `bundesland`).
- **No AI hallucinations (as medlyn):** an LLM never states a number or a fact itself. It only chooses tools, IDs and templates; text is rendered from query results. A claim check verifies every number in an agent answer against its source query before it is shown. Missing data is reported as „nicht vorhanden/nicht geliefert“, never guessed. Conflicting sources (e.g. a published month vs. a later delivery) are shown side by side, never silently resolved.
- **Source evidence everywhere:** every number and chart point in the web app links to its evidence – SQL, delivery file with SHA-256, run with checksum, applied rules with approver, classification version, and example records „wie geliefert“ vs. „wie gelesen“ (medlyn-style „Quellennachweis“ panel with cited rows and context).
- **Synthetic data and models:** generated data lives in its own schema `synth`, is labelled synthetic and never mixed with delivered data. Models (expected corridor, error detector) run locally with fixed seeds, are versioned with data and model hashes, and are evaluated on held-out synthetic data **and** on the real deliveries, with honest metrics. Predictions are labelled „Modell“, never written to `stat_*`, and never correct data – they only flag and propose; a human approves (T1, T7).
- **UI:** dynamic like medlyn – motion animations, streamed agent answers, live run progress, interactive charts (Recharts), transition graphs, highlighted SQL.

## Environment (Windows)

- PostgreSQL 16.15, Windows service `postgresql-x64-16`, port 5432; `psql` not on PATH: `"C:\Program Files\PostgreSQL\16\bin\psql.exe"`. DB/user/password `statistik` (`.env`, untracked).
- Python 3.10 venv `.venv` (pinned `requirements.txt`). Git `core.autocrlf=true` → `.gitattributes` keeps package files byte-identical.
- System Node v19.7 is too old for the Next.js 16 frontend → use the portable Node 22 in `C:\Users\pickm\tools\node22` (prepend to PATH) with pnpm 10.34.8 via corepack; web UI: `cd web; pnpm dev` → http://localhost:3000 (backend `statagent web` on :8000 must run), see `web/README.md`.
- Agent model: `.env` → `AGENT_API_KEY`, `AGENT_MODEL` (+ `AGENT_PROVIDER`, `AGENT_BASE_URL`, `AGENT_API_VERSION`); restart `statagent web` after changes. Never print or commit the key (`geheimnisse` scans for it).
- Remotes: development `git@github.com:Merrixx/Attentionseeker3-case3.git` (SSH, key with passphrase); submission `https://github.com/KIChallenge/AttentionSeekers3` (private, keeps its own YAML file; README = ours).

## Commands (`.venv\Scripts\python.exe -m statagent <cmd>`, logs in `logs/`)

| Command | Purpose |
| --- | --- |
| `migrieren` | schema: delivered `datenbank/01_schema.sql` once + `sql/*.sql` (idempotent) |
| `laden` / `pruefen` | load all package files unchanged (~1.5 min) / integrity check (checksums, 10,152,292 rows) |
| `bestand [--lieferung JJJJ-MM] [--vorschau R-…]` | build versioned store `store.segment` with approved rules (~4 min, 6 workers); preview = rolled back |
| `profil` | per-delivery problem matrix (= Problems.md §2.1) |
| `klassifikation [--nur-pruefen]` | rebuild all `klass_*`, `klass_uebergang`, `quellzuordnung` (~1 s) + check every delivered code (~10 s) |
| `erklaeren KLASS CODE [--version V]` | deterministic explanation of a code (KLASS = region, oenace, geschlecht, qualifikation, alter) |
| `regeln [ID]`, `freigeben ID --von "Name"`, `ablehnen ID --von "Name"` | rules and approvals |
| `protokoll` | export `protokoll/protokoll.md` + suggested commit message |
| `lauf --lieferung JJJJ-MM [--regelwerk basis\|auftraege] [--vorschau R-…]`, `gesamtlauf` | monthly run (~35 s) / 24 runs: stat_beschaeftigte, findings, QB, Rückfragen |
| `kalibrierung [--vorschau R-DQ05]`, `veroeffentlichen --von` | 2,880-cell test against the example report / named publication (freeze) |
| `aggregationen --regelwerk`, `ministerium`, `lieferung-freigeben DATEI --von` | sheet + Open-Data-File / ministry CSV (needs approved R-A3) / delivery release |
| `agent "…" --von [--probe]`, `frage "…"`, `code-freigeben`, `code-ausfuehren` | coordinator agent (proposals only) / chat answer / agent code (T6) |
| `sichern`, `wiederherstellen DATEI --ja` | database dump (0.5 GB, SHA-256) for another machine / restore (SW-19; dump never into git) |
| `pensionen`, `modelle`, `geheimnisse`, `web` | pension statistic / synthetic data + models / secret scan / JSON API on 127.0.0.1:8000 |

Verification anchors: 08/2024 Stichtag = 392,236 (= example report); 06/2025 = 394,252 with R-DQ01 (21 as delivered); `klassifikation` checksum `c37199e6…` (8,115 codes, 3,303 transitions, 91 mappings), code check: all 40,609,168 attribute values "ok".

Tests: `.venv\Scripts\python.exe -m pytest` (45 tests, pytest 8.4.2; integration tests roll back; `-m "not integration"` = 28 unit tests in < 1 s; `tests/test_agent.py` replaces the model by a fake). Frontend: `cd web; pnpm test:smoke` (app must run). Runbook and jury script: `docs/RUNBOOK.md`.

## Code map

- `statagent/etl/load.py` loader · `statagent/etl/store.py` store builder (rule actions, problem flags, profile, checksum)
- `statagent/etl/classification.py` classification builder (klass_*, transitions, source mappings, code check) · `statagent/reporting/explain.py` explainer
- `statagent/core/rules.py` approvals · `statagent/core/change_log.py` protocol export · `statagent/core/labels.py` German labels for enum values · `statagent/migration.py` · `statagent/cli.py` German command names on English functions
- `statagent/qa/run.py` monthly runs + gates · `qa/checks.py` findings/revisions/inquiries · `qa/report.py` QB · `qa/calibration.py`
- `statagent/reporting/tools.py` statistics tools (SQL + definition + evidence; `query_pension`) · `sources.py` „Verwendete Dateien“ per answer · `quality.py` dynamic DQ handling on a copy (`work.dq_copy`, kept 7 days; `adjust` for Verhältnisse, `recompute` for Personen/flows) · `core/backup.py` dump/restore · `claims.py` claim check · `sheet.py` Aggregations-Sheet · `ministry.py` order 3
- `statagent/agents/` `llm.py` provider-neutral model adapter (`AGENT_*` in `.env`: Anthropic/OpenAI/Azure/Gemini/compatible, retries without forced tool use) · `intent.py` German/English parser + scope gate (`DOMAIN`, `UNAVAILABLE`, pensions) · `chat.py` Fragen agent (7 tools, `apply_chart`, `pension_card`) · `coordinator.py` roles + proposals · `codegen.py` generated code (T6)
- `statagent/ml/` synthetic generator + corridor/detector · `statagent/etl/pensions.py` pension parsers · `statagent/api/` FastAPI · `web/` Next.js UI
- `sql/070` production (month_record, month_flow, report, revision) · `080` agents (answer, term, code_proposal, agent_task) · `090` models/synth · `100` pensions
- `sql/005` in-place rename of pre-refactor databases · `010` raw helper tables in `roh` · `020` Anhang-B model (public, German as prescribed) · `030` operations (`ops`: rule, approval, change_log, run, finding, inquiry) · `040` store (`store.segment`, `store.profile`) · `050` seeds + proposed rules · `060` classifications (views `klass_alle`, `quellzuordnung_wirksam`, rules R-DQ07/08)
- Enum values are English (`proposed/approved/rejected/retired`, `swap_columns`, `source_mapping`, run kinds `store/month/classification`); the UI shows them via `labels.py`. Rule set ID stays `basis` (also used in `stat_beschaeftigte.regelwerk`).
- Mapping rules (action `quellzuordnung`): the builder writes their rows from the rule parameters; only `quellzuordnung_wirksam` (no rule or approved rule) may be used for counting.

## Status (2026-11-06 08:00)

- Phases 0–8 implemented (Phases.md §1.1). Approved rules: R-DQ01/03/05/07/08/09 (Mercy); R-DQ02/04/10 stay proposed by team decision (handled per statistic in the chat, `statagent/reporting/quality.py`).
- Basis series recomputed and **published** (runs 148–171, all `endgueltig`), sheet regenerated – see `docs/RECOMPUTE.md`. Published months are frozen.
- Change orders 1–3 done 06.11. (agent task 14, runs 218–241, sheet + QBs `auftraege`, ministry CSV). Ministry delivery released 06.11. 07:30. Waiting for humans (never do these as a tool): commits, no Azure access received (ENV-10) – agent runs with Anthropic, switchable via `AGENT_*` in `.env`. Steps: `docs/RUNBOOK.md` §3. Frontend state: `web/STATUS.md`.
- Chat: data agent in „Fragen“: the model (Anthropic `claude-sonnet-5-5`; no Azure access received, ENV-10; switchable any time via `AGENT_*` in `.env`) picks one of 7 tools by function calling – employment, pensions, explain code, quality report, definition, not in data, decline out of scope; numbers only from SQL + claim check; every answer lists its files (SHA-256) and tables. Out-of-scope questions (history, physics, small talk) → „außerhalb des Datenbestands“; missing fields (Einkommen, Wohnort, …) → „nicht verfügbar“. Without a key the deterministic offline parser does the same. Model calls in `ops.llm_call`.
- Web: links between pages restored (Lieferungen ↔ Läufe ↔ QB ↔ Freigaben ↔ Protokoll, URL state `?monat`/`?lauf`/`?ansicht`/`?q`), `/fragen?frage=` deep link. Open bugs/limits: Problems.md §8.
- UI must copy the styling of https://github.com/Julian-AT/medlyn (`apps/app`) – CC BY-NC 4.0, used with permission.
