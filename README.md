# AttentionSeekers3 – StatAgent (KI Challenge 2026, Use Case 3)

An agent-supported, **deterministically calculating** statistics production for the Dachverband der Sozialversicherungsträger. It turns 24 monthly deliveries of insurance relationships (10,152,292 rows) into the official employment statistic, builds a pension statistic from 28 carrier reports in seven formats, maintains the metadata (classifications with versions and transitions), finds and documents data errors in 24 quality reports, answers data questions in a German chat with charts – and **never lets an AI invent a number**. Every number carries its evidence (Quellennachweis) and every change is approved by a named person.

| Document | Content |
| --- | --- |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | **how the submission was produced, what to run, and the jury script** |
| [docs/PRAESENTATION.md](docs/PRAESENTATION.md) | **Präsentationsskript für die Fachjury** (Ablauf, Sprechtext, Fragen und Antworten – besonders zu den Modellen) |
| [docs/RECOMPUTE.md](docs/RECOMPUTE.md) | what the recompute after the rule approvals did and why; fresh-clone steps |
| [StateOfDevelopment.md](StateOfDevelopment.md) | state, architecture, tech stack, rules and scoring |
| [Problems.md](Problems.md) | every issue found in data, package and specification, with evidence |
| [Phases.md](Phases.md) | implementation plan and progress |
| [abgabe/MODELLE.md](abgabe/MODELLE.md) | models used: language model for the agents (no Azure access received → Anthropic, switchable via `.env`) and our own corridor/detector with metrics and limits |
| [abgabe/protokoll/protokoll.md](abgabe/protokoll/protokoll.md) | protocol of all approved changes (T8) |
| [docs/PRD.md](docs/PRD.md), [docs/references.md](docs/references.md) | original requirements / build plan (historical), prior art and licences |
| [web/STATUS.md](web/STATUS.md), [web/README.md](web/README.md) | web frontend: pages, conventions, known issues, start commands |
| [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) | licences of dependencies and styling |
| `SV md files/` | task documents and the original package README |

## Approach

- **The program calculates, the AI does not (T1).** Numbers come only from parameterised SQL/Python. Same data + rules → same numbers; every run stores a checksum (verified: two runs of 08/2024 give `6e3d2952…`).
- **No delivered data is edited.** All 115 package files are loaded unchanged and registered with SHA-256; `pruefen` proves nothing changed. Errors are flagged per record and handled only by **reading rules** applied at read time. Faulty records stay in every statistic.
- **No relationship is lost (Anhang A 1).** Every run fails if a VVH active on the Stichtag is not counted exactly once; reconciliation *gelesen = gezählt + nicht gezählt + ausgeschlossen* is checked per month; unmapped values go to a visible „nicht zuordenbar“ code.
- **Rules as data, approved by a person (T3, T7).** Rules live in `ops.rule` with assumption and justification, take effect only after a named approval (names like „Team“ or „Agent“ are rejected), and are listed with their effect in every quality report.
- **Calibrated on the example report.** All **2,880 numeric cells** of `beispielbericht_2024-08.xlsx` (Tab1–Tab13) are recomputed from `stat_beschaeftigte` (`kalibrierung`).
- **Agents prepare, people approve (T5–T8).** A coordinator routes German instructions to four roles (Datenmanagement, Klassifikation, Qualitätssicherung, Reporting). They create rule or code proposals with diff and before/after numbers; generated code is a readable file that runs without an LLM and only if its exact SHA-256 was approved.
- **No AI hallucinations (medlyn pattern).** In „Fragen“ a data agent (language model via `.env`, offline parser without a key) picks one of seven tools and its parameters – or declines questions outside the data („außerhalb des Datenbestands“) and fields that were never delivered („nicht verfügbar“). The chat asks back if a term is ambiguous („Fluktuation“ → three readings), runs deterministic SQL, renders a StatCard and a template text, and a **claim check** verifies every number in the text against the query result before it is shown (fail closed). Missing data is answered with „nicht vorhanden“.
- **Faulty data is handled per statistic, not hard-coded.** Only the rules the team approved apply to the published series. When someone asks for a statistic, the chat marks every data problem that touches the requested months and fields (e.g. month-13 birth dates for an age breakdown, the incomplete delivery 2025-10, empty Bundesland) and offers three handling options plus free text. The choice is applied to a copy of only the affected records (`work.dq_copy`); the card shows the result next to the official value. Free text is mapped to an option or kept as a note – never executed.
- **More Rückfragen.** Besides „Fluktuation“, the term catalogue (`ops.term`, data) asks back for „Menschen/Arbeitnehmer“ (Verhältnisse vs. Personen), „Arbeiter/Angestellte“ (with/without freie Dienstverträge), a bare year (average / year end / all months), „Entwicklung“ for one month, „Alter“ (single years / 5- / 10-year groups) and periods across the ÖNACE break.
- **Synthetic data and models stay apart.** A seeded generator calibrated on the real runs plants labelled errors; a detector and an expected corridor are trained on it and evaluated separately on held-out synthetic data and the 24 real deliveries. Models only flag – schema `synth`, never `stat_*`.
- **English code, German surface.** Code, logs and own schemas (`ops`, `store`, `synth`) are English; the Anhang-B model, CLI commands, web UI and reports are German.

## Prerequisites

- Windows, macOS or Linux; **Python ≥ 3.10**; **PostgreSQL ≥ 14** (developed with 16.15) on `localhost:5432`; ~4 GB disk
- Web UI: **Node.js ≥ 20.9** (developed with Node 22.23.4 portable) and **pnpm 10** (via corepack)

## Setup

```powershell
git clone https://github.com/KIChallenge/AttentionSeekers3.git; cd AttentionSeekers3
psql -U postgres -h localhost -c "CREATE USER statistik WITH PASSWORD 'statistik';" -c "CREATE DATABASE statistik OWNER statistik;"
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env          # DB settings; optional: STATAGENT_USERS, AGENT_API_KEY/AGENT_MODEL (never committed)
cd web; corepack enable; pnpm install; cd ..
```

## Running

Console (everything is available here; logs in `logs/`): `.venv\Scripts\python.exe -m statagent <Befehl>`

| Command | What it does |
| --- | --- |
| `migrieren` · `laden` · `pruefen` | schema · load all package files unchanged (~1.5 min) · integrity check (checksums, 10,152,292 rows) |
| `bestand` · `profil` | versioned store `store.segment` with approved reading rules (~4 min) · delivery problem matrix |
| `klassifikation` · `erklaeren KLASS CODE` | classifications, transitions, source mappings (~1 s) · deterministic explanation, e.g. `erklaeren region 62388` |
| `lauf --lieferung JJJJ-MM [--regelwerk basis\|auftraege] [--vorschau R-…]` | **monthly run**: Z1–Z8, gates, `stat_beschaeftigte`, findings, QB, Rückfragen (~35 s) |
| `gesamtlauf [--regelwerk …]` | 24 single runs in order (~14 min) |
| `kalibrierung [--vorschau R-DQ05]` | cell-by-cell test against the example report |
| `veroeffentlichen --von "Name"` | publish (freeze) finished months – named approval |
| `aggregationen --regelwerk basis\|auftraege` | Aggregations-Sheet from the template + Open-Data-File |
| `ministerium` · `lieferung-freigeben DATEI --von "Name"` | ministry delivery (change order 3, after approval of R-A3) · named release of a delivery |
| `agent "Anweisung" --von "Name" [--probe]` | instruction to the coordinator agent (proposals only; `--probe` = rolled back) |
| `frage "…" [--lesart fluktuation=c]` | data question with SQL, definition and claim check |
| `regeln` · `freigeben ID --von` · `ablehnen ID --von` | rules and named approvals |
| `code-freigeben C-0001 --von` · `code-ausfuehren C-0001 --von` | approve / run agent-generated code (T6) |
| `pensionen` · `modelle` | pension statistic (~10 s) · synthetic data + corridor + detector (~10 min) |
| `sichern` · `wiederherstellen DATEI --ja` | database dump (0.5 GB, SHA-256, not in git) · restore it on another machine |
| `protokoll` · `freigaben-wiederherstellen` · `geheimnisse` · `web` | protocol export + `abgabe/protokoll/freigaben.json` + commit message · restore rule decisions in a fresh clone · secret scan · JSON API |

Web UI (two terminals):
```powershell
.venv\Scripts\python.exe -m statagent web                       # API on http://127.0.0.1:8000 (local only)
cd web; pnpm dev                                                 # UI on http://localhost:3000
```
Pages: Übersicht · Lieferungen · Läufe · Qualitätsberichte · Klassifikationen · Pensionen · Dashboard · Modelle · Fragen · Agent · Freigaben · Protokoll · Exporte. Login = choose a named person (used for approvals).

Fresh clone (the database is not in git): fastest with a dump from `sichern` → `wiederherstellen DATEI --ja` → `pruefen`. Without a dump: `migrieren → laden → pruefen → freigaben-wiederherstellen → klassifikation → bestand → gesamtlauf → kalibrierung → aggregationen`. `freigaben-wiederherstellen` re-applies the team's rule decisions from `abgabe/protokoll/freigaben.json` (written by `protokoll`), but only for rules whose action and parameters are unchanged; publication (`veroeffentlichen`) is a new decision by a person. Then change orders as in [docs/RUNBOOK.md](docs/RUNBOOK.md).

Tests: `.venv\Scripts\python.exe -m pytest` (45 tests; `-m "not integration"` for the fast unit tests; frontend: `cd web; pnpm test:smoke`: claim check, intent parser, data agent with a fake model, generated-code guard, ministry plan; integration tests against the DB for reconciliation, reproducibility, calibration, sheet totals, approval gates and read-only access – all rolled back).

## Deliverables (`abgabe/`)

| Deliverable | File(s) |
| --- | --- |
| Aggregations-Sheet, old rules | `abgabe/aggregationen_basis.xlsx` (+ `stat_beschaeftigte_basis.csv.gz` = Open-Data-File) |
| Aggregations-Sheet after the change orders | `abgabe/aggregationen_auftraege.xlsx` (+ `stat_beschaeftigte_auftraege.csv.gz`) |
| 24 quality reports | `abgabe/qualitaetsberichte/basis/QB_JJJJ-MM.md` and `abgabe/qualitaetsberichte/auftraege/QB_JJJJ-MM.md` |
| Rückfragen | `abgabe/rueckfragen/RF-DQ02.md`, `RF-DQ04.md`, `RF-DQ16.md` |
| Calibration | `abgabe/kalibrierung_2024-08.md` |
| Ministry delivery 07/2026 | `abgabe/ministerium_2026-07.csv` (32,741 persons, released 06.11.2026) |
| Protocol | `abgabe/protokoll/protokoll.md` |
| Models statement | `abgabe/MODELLE.md` |

## Configuration (`.env`)

| Variable | Meaning |
| --- | --- |
| `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` | database (package defaults `statistik`) |
| `STATAGENT_USERS` | comma-separated list of named persons offered at login; these names are always accepted as approvers (free entry is possible, placeholders like „Test“ are rejected) |
| `STATAGENT_FRAGEN_PERSON` | name logged for questions in „Fragen“ when nobody is logged in (default „Gast“) |
| `AGENT_API_KEY`, `AGENT_MODEL` (+ `AGENT_PROVIDER`, `AGENT_BASE_URL`, `AGENT_API_VERSION` if needed; old `AZURE_OPENAI_*` still work) | optional: the language model of the data agent (OpenAI, Anthropic, Azure, Gemini or any OpenAI-compatible server; provider detected from the key). It picks the tool and parameters or declines questions outside the data – never numbers. Without a key the chat runs in the labelled offline mode |

## Known limitations and open points

- **Done by the team (2026-11-06):** R-DQ03/05/09 approved, basis series recomputed and published (see docs/RECOMPUTE.md). R-DQ02/04/10 deliberately not approved – handled per statistic in the chat.
- **Change orders done (2026-11-06):** the three instructions were given to our agents in German, approved (R-A1/R-A2/R-A3) and carried out by the agent: 24 runs in the rule set `auftraege`, its sheet and quality reports, and the ministry delivery (released). Every step is in `abgabe/protokoll/protokoll.md`. The `auftraege` series is labelled „vorläufig“ (publishing it is the team's decision).
- Calibration: **bestanden** – totals and Tab1–Tab12 match; the 359 age cells that differ vanish completely when the 370 month-13 birth dates are read like the example report (birth year) instead of with the approved R-DQ05 swap; both variants are in `abgabe/kalibrierung_2024-08.md`.
- Database for another machine: `statagent sichern` (0.5 GB dump with SHA-256, not in git) and `statagent wiederherstellen DATEI --ja` instead of the ~30 min rebuild.
- **Language model (ENV-10):** no access to the Azure model was received; the agent runs with Anthropic `claude-sonnet-5-5` (key in `.env`, not committed). The model can be switched at any time via `AGENT_*` in `.env` (restart `statagent web`); without a key the chat runs in the labelled offline mode.
- Open points and known limitations are listed in Problems.md §8. With the model, free wording (also English) is understood; the agent declines questions outside the data and reports fields that were never delivered. Offline, the parser understands the documented question types; unknown phrasing leads to a Rückfrage, not a guess.
- Models: honest metrics but tiny real samples (one affected delivery per error type); see abgabe/MODELLE.md.
- `SV md files/Use Case 3 StatAgent.pdf/.md` are not in the repo because they contain the SV-BOX password.

## Data and licences

- The package data is synthetic and public (SV-BOX). Regional data: CC BY 4.0, **Quelle: Statistik Austria**.
- UI styling copied from [medlyn](https://github.com/Julian-AT/medlyn) (CC BY-NC 4.0) with the author's permission, non-commercial; see `web/NOTICE.md`. Dependencies: [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
