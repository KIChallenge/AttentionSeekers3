# Problems – StatAgent (KI Challenge 2026, Use Case 3)

This is the single list of **all current issues** in `SV usecase3`. Status as of 2026-11-05. Every number was measured on the delivered files.

Related: [StateOfDevelopment.md](StateOfDevelopment.md) (state, tech stack, rules) · [Phases.md](Phases.md) (plan).

## 0 Handling policy

1. **No data is edited.** Package files and `roh.*` stay exactly as delivered: no renaming, deleting, re-encoding or fixing.
2. **Errors are part of the challenge.** Each one is listed here with evidence (delivery, number of records, example IDs) and appears in the month's quality report (QB).
3. **No record is dropped.** Faulty records stay in every statistic and graph (Anhang A rule 1).
4. **Where an error affects a value**, a documented **reading rule** applies at read time and nothing is written back. Graphs mark the affected part and offer an **"as delivered"** view.
5. Every reading rule names its assumption, justification, affected records and start month, and is approved by a named person.

Severity: **High** = changes totals by > 0.1 % or loses relationships · **Medium** = changes breakdowns or derived results · **Low** = plausibility or cosmetic.

---

## 1 Overview

| ID | Problem | Severity | Where |
| --- | --- | --- | --- |
| DQ-01 | BEGINN and ENDE columns swapped | High | 2025-06 |
| DQ-02 | delivery incomplete (~20 % of VVH missing) | High | 2025-10 |
| DQ-03 | exact duplicate rows | High | 2025-03 |
| DQ-04 | all freie Dienstverträge missing | High | 2025-03 |
| DQ-16 | phantom double registrations | Medium | every delivery |
| DQ-05 | birth dates with month 13 | Medium | every delivery |
| DQ-07 | outdated ÖNACE-2003 codes | Medium | every delivery |
| DQ-08 | OENACE and BUNDESLAND empty | Medium | every delivery |
| DQ-12 | late reports change published months | Medium | every month |
| DQ-13 | ÖNACE switch recodes history | Medium | L2025-01 |
| DQ-06 | implausible birth dates (age > 110) | Low | every delivery |
| DQ-09 – DQ-11 | overlapping, gapped or doubly-open segments | Low | single VVH |
| DQ-14 | age heaping at 74 | Low | every delivery |
| DQ-15 | no "unbekannt" entry for Geschlecht/Qualifikation | Low | classification files |
| DQ-17 | segment starts before the 15th birthday | Low | rising, 2 → 56 rows |
| PEN-01 – 09 | pension formats, format changes, text numbers, mergers | Medium | `pensionen/` |
| KL-01 – 08 | classification files: duplicates, encoding, transitions, inconsistent change dates | Medium | `klassifikationen/` |
| ENV-01 – 16 | package files and this machine | Medium | package, PC |
| SPEC-01 – 07 | ambiguities in the task documents | Medium | docs |
| RD-01 – 06 | **real developments – not errors, must not be "corrected"** | – | – |
| SW-01 – 32, W-01 – 14 | known bugs and limitations of StatAgent itself (§8) | – | software |

---

## 2 Delivery data (DQ)

### 2.1 Per-delivery matrix

"Active" is the number of VVH active on the month's last day from the month's own delivery, each VVH counted once, with 2025-06 read in the order its values imply; DQ-02, DQ-04 and DQ-16 are not handled in it. "Phantom" is the number of VVH open at month end that are entirely absent from the next delivery (DQ-16).

| Delivery | Rows | Active | Dups | Month 13 | Age > 110 | ÖNACE 2003 | No ÖNACE/BL | Overl. | Gaps | Start < 15 | Phantom | Note |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2024-08 | 392,284 | 392,236 | 0 | 370 | 7 | 50 | 1,996 | 0 | 0 | 2 | 196 | = example report |
| 2024-09 | 407,526 | 393,454 | 0 | 382 | 8 | 50 | 2,083 | 3 | 1 | 2 | 203 | DQ-11 (1 VVH) |
| 2024-10 | 420,576 | 391,033 | 0 | 393 | 9 | 50 | 2,147 | 3 | 2 | 2 | 210 | |
| 2024-11 | 426,559 | 389,141 | 0 | 395 | 9 | 50 | 2,160 | 3 | 3 | 3 | 213 | |
| 2024-12 | 426,546 | 387,390 | 0 | 399 | 10 | 50 | 2,157 | 2 | 0 | 4 | 213 | last ÖNACE 2008 |
| 2025-01 | 424,363 | 385,033 | 0 | 406 | 11 | 50 | 2,154 | 1 | 2 | 7 | 212 | ÖNACE 2025 (DQ-13) |
| 2025-02 | 424,641 | 386,996 | 0 | 405 | 10 | 50 | 2,150 | 3 | 0 | 9 | 212 | |
| 2025-03 | 425,151 | 387,180 | **1,663** | 399 | 10 | 50 | 2,163 | 1 | 2 | 11 | 212 | **no FD (DQ-04)** |
| 2025-04 | 425,831 | 387,601 | 0 | 404 | 10 | 50 | 2,175 | 0 | 1 | 10 | 212 | |
| 2025-05 | 428,948 | 390,001 | 0 | 415 | 10 | 50 | 2,174 | 4 | 7 | 12 | 214 | |
| 2025-06 | 432,086 | 394,252 | 0 | 412 | 12 | 50 | 2,184 | 1 | 0 | 16 | 215 | **swapped (DQ-01)**; 21 as delivered |
| 2025-07 | 435,070 | 397,419 | 0 | 423 | 11 | 50 | 2,187 | 2 | 6 | 18 | 217 | |
| 2025-08 | 433,286 | 393,712 | 0 | 424 | 11 | 50 | 2,192 | 4 | 1 | 20 | 216 | |
| 2025-09 | 434,104 | 394,200 | 0 | 435 | 11 | 51 | 2,186 | 0 | 1 | 26 | 216 | |
| 2025-10 | **345,078** | **313,154** | 0 | 336 | 7 | 40 | 1,742 | 2 | 1 | 24 | 131 | **incomplete (DQ-02)** |
| 2025-11 | 428,277 | 389,823 | 0 | 422 | 11 | 50 | 2,159 | 2 | 1 | 35 | 214 | |
| 2025-12 | 427,870 | 388,231 | 0 | 429 | 11 | 49 | 2,141 | 3 | 0 | 37 | 213 | |
| 2026-01 | 425,360 | 385,573 | 0 | 424 | 11 | 49 | 2,143 | 2 | 2 | 37 | 212 | |
| 2026-02 | 426,706 | 387,947 | 0 | 419 | 11 | 49 | 2,136 | 2 | 3 | 38 | 213 | |
| 2026-03 | 428,560 | 391,475 | 0 | 425 | 11 | 49 | 2,156 | 1 | 1 | 51 | 214 | |
| 2026-04 | 428,910 | 389,361 | 0 | 417 | 11 | 49 | 2,169 | 1 | 2 | 52 | 214 | |
| 2026-05 | 431,862 | 391,871 | 0 | 416 | 9 | 49 | 2,175 | 2 | 3 | 59 | 215 | |
| 2026-06 | 434,517 | 395,320 | 0 | 426 | 8 | 49 | 2,170 | 2 | 4 | 56 | 217 | |
| 2026-07 | 438,181 | 399,027 | 0 | 444 | 9 | 49 | 2,177 | 1 | 1 | 56 | n/a | ministry month; no later delivery |

Total: **10,152,292 rows**.

Checked and **not** found:
- header changes
- invalid GESCHLECHT/QUAL/BUNDESLAND codes (only empty values occur)
- non-ISO dates, BEGINN after the reporting date, ENDE in the future
- records outside the 3-month window
- a VVH whose PERSON_ID, GEBURTSDATUM or GESCHLECHT changes; reused VVH_IDs
- persons under 15
- ÖNACE-2025 codes before 01/2025, ÖNACE-2008 codes after 01/2025

### 2.2 Details

**DQ-01 – BEGINN/ENDE swapped (2025-06, High)**
- Evidence: 388,115 rows have an empty BEGINN and a filled ENDE; 43,914 have ENDE < BEGINN; only 57 rows look normal.
- Examples: VVH 7 (– / 2024-04-15), 12 (– / 2024-06-22), 13 (2025-05-04 / 2024-08-29).
- As delivered: only **21** VVH are active on 30.06.2025, instead of 394,252.
- Reading rule: read the two columns swapped, triggered by > 50 % empty BEGINN or ENDE < BEGINN. L2025-07 confirms this reading. Graph: 06/2025 marked; the "as delivered" view shows the collapse.

**DQ-02 – Incomplete delivery (2025-10, High)**
- Evidence: 345,078 rows instead of ~430k.
  - 78,763 VVH that are active on 31.10. according to L2025-11 are absent from L2025-10.
  - The loss is random: evenly spread over Bundesland, Qualifikation, sex, ÖNACE and the ID range.
  - Aug/Sep inside L2025-10 are also −20 % (314,642 / 315,303).
- Examples: VVH 34, 79, 95, 122, 139.
- As delivered: 10/2025 = 313,154, a −20 % jump.
- Handling:
  - the jump check flags it
  - an assumption view carries forward the VVH still open in L2025-09 (only earlier deliveries are allowed)
  - revision in QB 2025-11; **Rückfrage recommended**
  - graph shows "as delivered" and "with assumption"
  - proposed rule **R-DQ02** (carry-forward of the 77,510 VVH open in L2025-09 and absent from L2025-10, phantoms excluded); Rückfrage RF-DQ02
  - **ministry delivery (order 3):** the days of 08/2025 come from L2025-10 (latest delivery containing them) – without handling, 74 persons drop below 200 days (32,741 → 32,667); rule R-A3 uses L2025-09 for VVH missing completely from L2025-10

**DQ-03 – Exact duplicates (2025-03, High)**
- Evidence: 1,663 identical rows, so 1,523 VVH have 2 active segments on the Stichtag.
- Examples: VVH 291, 355, 387, 511, 517.
- As delivered: counting rows gives 388,703 instead of 387,180.
- Handling: count the VVH once; **R-DQ03 approved** (Mercy, 05.11.) – copies marked as not counted, the rows stay in `roh` and `store`.

**DQ-04 – Freie Dienstverträge missing (2025-03, High)**
- Evidence: 1,651 FD VVH in L2025-02 → 0 in L2025-03 → 1,524 back in L2025-04.
- Examples: VVH 448, 1054, 1264, 1289, 2247.
- As delivered: the FD rows are 0 and the total is −1,651. Revisions computed from L2025-03 for Jan/Feb show artificial differences.
- Handling: flagged by the category-share check (= 0); an assumption view carries forward from L2025-02; revision in QB 2025-04; **Rückfrage recommended**. Not a real development.

**DQ-16 – Phantom double registrations (every delivery, Medium)**
- Evidence: in every delivery the ~200 **highest VVH_IDs** are new VVH that:
  - start in the reporting month and are still open
  - belong to a person who already has an open VVH with **identical QUAL/OENACE/BUNDESLAND**
  - are **all gone in the next delivery**
- Examples:
  - L2024-08: VVH 859780–859975 (196), e.g. VVH 859780 = person 1315805, who has had VVH 315806 since 2014-05-14
  - L2025-12: VVH 863170–863382 (213)
- As delivered: each month is ~200 too high (~0.05 %). **The example report includes them.**
- Detection from the own delivery only: "new VVH in the reporting month + older open VVH of the same person with identical attributes". It finds 207/189, 300/212 and 293/214 (candidates / truly vanishing) in 08/2024, 05/2025 and 06/2026; the remaining candidates are probably genuine second jobs.
- Handling: counted as delivered; flagged in the month's QB; confirmed as revision need in the next QB; Rückfrage; optional sensitivity view.

**DQ-05 – Birth month 13 (every delivery, Medium)**
- Evidence: `YYYY-13-DD`, 336–444 rows per delivery. The day is always ≤ 28, so this is **not a day/month swap** (a swap would give month 28). Only the year is usable.
- Examples (L2024-08): VVH 1050, 1824, 2257, 5493, 7739.
- As delivered: a strict parser puts them into "Alter unbekannt"; the example report instead uses age = report year − birth year.
- Handling (team decision 2026-11-05): **R-DQ05 reworked** – flagged as a wrong date format and read with day and month swapped (JJJJ-TT-13) where TT ≤ 12 (08/2024: 143 of 370); otherwise fallback „unbekannt“ (parameter); optional parameter `exclude` (excluded records are shown, not lost). This deviates from the example report's year-based age (359 age cells of Tab13). In the chat each statistic with an age breakdown offers: Tag/Monat tauschen · Alter unbekannt · ausschließen (+ free text), applied on a copy (`work.dq_copy`). Ministry: GEBURTSJAHR = year.

**DQ-06 – Age > 110 (every delivery, Low)**
- Evidence: 7–12 per delivery, e.g. 1850-12-14, 1871-01-09, 1907-05-24.
- Examples: VVH 52095, 108302, 149431, 207859, 327231.
- Handling: age `unbekannt` (example report: 7); counted in all other dimensions; ministry GEBURTSJAHR `Unbekannt`.

**DQ-07 – ÖNACE-2003 codes (every delivery, Medium)**
- Evidence: `DA DB DC DD DF DG DH DI DJ DK DL DM` (subsections of "D – Sachgütererzeugung") on 40–51 long-running VVH, also after 01/2025.
- Examples: VVH 1005 (DH), 1344 (DJ), 11805 (DD), 35951 (DA), 37237 (DA).
- As delivered: no ÖNACE sheet row matches, so that sheet is 50 short. Do not confuse with 2008 `D` (Energieversorgung).
- Handling: mapping rule **R-DQ07**, approved by Mercy on 2026-11-05 (Quellzuordnung `DA…DM` → section C of the ÖNACE valid in the reporting month, 2008 or 2025). Official Umsteiger: 500 of 520 Unterklassen correspondences of these subsections lead to 2008 C (96 %), 325 of 327 from 2008 C to 2025 C; `DE`/`DN` (partly J, E/S) do not occur. The example report confirms C = 62,154 + 50. The graph marks the share.

**DQ-08 – Empty ÖNACE and Bundesland (every delivery, Medium)**
- Evidence: both empty together, 1,742–2,192 rows; mostly the same VVH over time, so nothing can be filled from history.
- Examples: VVH 153, 291, 350, 389, 542.
- Handling: mapping rule **R-DQ08**, approved by Mercy on 2026-11-05: empty → `Bundesland unbekannt` (0) and `UNB` (as a precaution also empty GESCHLECHT/QUAL → `UNB`), shown as their own bar (example report: 1,996).

**DQ-09 / DQ-10 / DQ-11 – Segment structure (Low)**
- Overlaps (0–4 VVH/delivery): e.g. VVH 177707 has 2017-09-01–2024-08-31 and 2024-08-10–open; also 180480, 9389.
- Gaps (0–7 VVH/delivery; violates "lückenlos"): e.g. VVH 169362 ends 2024-08-31 and the next segment starts 2024-09-25.
- Open segment followed by another segment: VVH 56000 in L2024-09.
- Effect: possible double counting or wrong attributes on a Stichtag, an ambiguous "last segment" (order 2), missing days (order 3).
- Handling: the later segment takes precedence from its BEGINN; decide whether a gap counts as employment; document it in the QB.
- Status (2026-11-06): **R-DQ09 approved** (Mercy) and applied – 09/2024 = 393,453 (−1, VVH 56000); R-DQ10 (close gaps) deliberately not approved, gaps stay visible and are handled per statistic in the chat.
  - The preview shows that R-DQ09 lowers 09/2024 by one VVH: VVH 56000's open segment then ends before its one-day segment of 2024-08-31.

**DQ-12 – Late reports (Medium)**
- Evidence: ~13–15k segments per delivery get a new ENDE. A published month moves by 10 to ~700 VVH (e.g. 08/2024: 392,236 → 392,932 in L2024-09).
- Handling: published months stay unchanged; revision need in the QB, kept apart from the artefacts of DQ-02/04/16. The graph can show "published" vs "current".

**DQ-13 – ÖNACE switch recodes history (L2025-01, Medium)**
- Evidence: the same Nov/Dec 2024 segments are recoded in L2025-01.
  - shifts: J→K 9,963 · K→L 9,708 · L→M 4,587 · M→N 22,749 · N→O 24,330 · O→P 63,150 · P→Q 13,323 · Q→R 34,087 · R→S 4,844 · S→T 8,911 · T→U 323 · U→V 86
  - splits: G→T 2,845 · S→R 422 · F→M 301 · G→C 113
- Handling: compare revisions via the Übergänge or without ÖNACE. The graph shows the break at 01/2025 (RD-03).

**DQ-14 – Age heaping at 74 (Low).** 205 persons are aged 74 vs 47 aged 73 (08/2024), also in the example report. Counted as delivered; QB "investigated, not corrected".

**DQ-15 – No "unbekannt" entry (Low).** `geschlecht.csv` and `qualifikation.csv` have none, although the Fachbeschreibung says every classification does. There is no impact today. **Done:** `UNB` added in our own `klass_geschlecht`, `klass_qualifikation` and `klass_alter` (the CSVs stay unchanged).

**DQ-17 – Start before the 15th birthday (Low).** BEGINN is earlier than the 15th birthday: 2 rows (08/2024) rising to 56 (2026); e.g. VVH 5488, 172370. No count impact; plausibility finding in the QB.

---

## 3 Pension data (PEN) – `pensionen/`

Internal totals are consistent in every file. The issues are structural.

| ID | Problem | Handling (files unchanged) |
| --- | --- | --- |
| PEN-01 | **handled 2026-11-05** (`statagent/etl/pensions.py`, 378 sum checks) – 5 format families: PVA wide with a merged 2-row header · SVA/SVB code columns (`GES, GEM_M …`) + "Legende" · VAEB/BVAEB one sheet with blocks A/B · VAN long · SVS long | one parser per family → common long format |
| PEN-02 | format changes: **PVA from 2022** (new sheets, single-row header, **women before men**) · **SVS from 2023** (Sparte as text instead of `GW/LW`, `m/w` instead of `M/W`, extra column `Zeitraum`) | detect by header text, never by position or year |
| PEN-03 | numbers stored as text with "." thousands separators (`18.429`), 15 cells per VAEB/BVAEB file | parse as integers (18429), not decimals |
| PEN-04 | VAN has no Tabelle 13 ("nicht gesondert gemeldet") | status "nicht gemeldet" ≠ 0; footnote |
| PEN-05 | sub-areas are former carriers (PVA Arbeiter/Angestellte, Eisenbahn/Bergbau, GW/LW), not Qualifikation | `klass_versicherungstraeger` hierarchy |
| PEN-06 | mergers on 1.1.2020: SVA+SVB → SVS, VAEB+BVA → BVAEB, VAN → SVS; no separate Notariat area in SVS after 2020 | validity + n:1 transitions; series-break footnote |
| PEN-07 | totals over all carriers (Insgesamt, PV der Unselbständigen, PV der Selbständigen) not delivered | compute them |
| PEN-08 | sex written 7 ways (Männer/Frauen, Witwer/Witwen, `_M/_F`, `_m/_w`, M/W, m/w, männlich/weiblich) | Quellzuordnung → `klass_geschlecht` |
| PEN-09 | pension types need a classification (Tab 12: GEM, ALT, WIT, WAI; Tab 13: LVD, KOR, LZV, SA1, SA2) | `klass_pensionsart` |

## 4 Classification resources (KL) – `klassifikationen/`

Status 2026-11-05: all handled by `python -m statagent klassifikation` (findings printed with every build).

| ID | Problem | Handling (files unchanged) |
| --- | --- | --- |
| KL-01 | Bundesland exists twice: `bundesland.csv` (with 0) and `regionen/bundeslaender.csv` (without) | **done**: one `klass_region` (Bundesland/Bezirk/Gemeinde); labels 1–9 are identical, code 0 from `bundesland.csv` |
| KL-02 | ÖNACE `.txt` files are cp1252 + CRLF; 4 output forms; EDV vs display code; m:n correspondences | **done**: one `klass_oenace` (versions 2003/2008/2025, all levels); code = EDV code, display code in `attribute.code_anzeige`; relation types computed from the Umsteiger |
| KL-03 | region transitions exist only implicitly: 16 snapshots + change lists as ODS (several sheets) and PDF | **done**: states from the snapshots, transitions from the ODS sheets (Kennziffernänderungen, Zusammenlegungen, Teilungen, Bezirkszusammenlegungen, Namensänderungen) + same-code state changes; Bezirk transitions derived. Cross-check: every vanished/new Gemeinde and Bezirk code has a transition. PDFs not used yet |
| KL-04 | deliveries carry only the Bundesland | Gemeinde/Bezirk history only for the classification score |
| KL-05 | labels change between versions (e.g. G "Handel; Instandhaltung …" 2008 vs "Handel" 2025) | **done**: version-specific labels; sections use the basic-set label, the official title is kept in `attribute.titel` |
| KL-06 | ODS in-force dates contradict the snapshots: `62307 → 62388` "in Kraft 02.01.2015" and `62310 → 62388` "03.01.2015", but Stand 01.01.2015 already shows 62388 Sankt Peter am Ottersbach (merged with 62362 on 01.01.2015); legal basis given as LGBl. STM. Nr. 031/2015 and **031/2016** | transitions kept with the ODS date and a note; relation type (n:1) computed per state boundary |
| KL-07 | ODS format: title row above the header, a "Stand" footer row, mixed date formats (`2017-01-01T00:00:00` and `01.08.2023`), trailing spaces in headers and names | header found by content, dates parsed in both formats, values trimmed |
| KL-08 | basic-set label of ÖNACE 2025 `U` ("…; Herstellung von Waren …") differs from the official title ("… SOWIE HERSTELLUNG VON WAREN …") | basic-set label used (it is the Fachabteilung's), official title kept |

Not an error: 70604 Fließ was renamed to "Fliess" on 25.08.2015 and back on 06.10.2015 (ODS); both snapshots show "Fließ".

## 5 Package and environment (ENV)

| ID | Problem | Handling (without editing) |
| --- | --- | --- |
| ENV-01 | ~~compose file delivered as `docker-compose(1).yml`~~ **resolved 2026-11-05**: renamed by the team to `docker-compose.yml` | – |
| ENV-02 | ~~no DB runtime on this PC~~ **resolved 2026-11-05**: PostgreSQL 16.15 installed as Windows service `postgresql-x64-16`, port 5432 (`bin` not on PATH: use `C:\Program Files\PostgreSQL\16\bin\psql.exe`) | – |
| ENV-03 | folder `regionen/A╠ênderungen` is a broken `Änderungen` (macOS name damaged on unzip) | find it by pattern / Unicode-normalised name |
| ENV-04 | `.DS_Store` files in 3 folders | loaders skip them; `.gitignore` |
| ENV-05 | the package README references `Aufgabenstellung_StatAgent.md` (does not exist) and expects the docs in the root (the team moved them, and in the repo also the package README itself, to `SV md files/`); two task versions (23.10. MD vs 27.10. PDF) | use the 27.10. version |
| ENV-06 | mixed encodings and formats: UTF-8 CSV, cp1252 TXT, XLSX, ODS, PDF | explicit encodings; ODS/PDF readers |
| ENV-07 | `02_laden.sql` loads only deliveries + 5 basic CSVs; no versions, validity or hierarchy in the schema | own loader + own schema next to the delivered one |
| ENV-08 | **SV-BOX password** in `SV md files/Use Case 3 StatAgent.pdf/.md`, while the repo is public and publishing passwords is forbidden | exclude these files via `.gitignore`; keys only in `.env` |
| ENV-09 | ~~no git repository~~ **resolved 2026-11-05**: the project is in the team repo `Merrixx/Attentionseeker3-case3` (SSH; port 22 needed); `core.autocrlf=true` is neutralised for package files by `.gitattributes` | commits by the team, one per change, with `Freigegeben-von:` |
| ENV-10 | No access to the Azure model was received: neither endpoint nor key was provided (status 2026-11-06) | exchangeable adapter `statagent/agents/llm.py`, config in `.env`; developed and tested with Anthropic `claude-sonnet-5-5` instead; the model can be switched at any time via `AGENT_*` in `.env` (no code change, restart `statagent web`); without a key the labelled offline mode runs (deterministic intent parser) |
| ENV-11 | the Aggregations-Sheet template refers to an "Open-Data-File" that is not in the package | interpret as `stat_beschaeftigte`; Rückfrage possible |
| ENV-12 | 10,152,292 raw rows | indexes, `ANALYZE`, `NOT EXISTS`, log file, `python -u` |
| ENV-13 | ~~Python packages missing~~ **resolved 2026-11-05**: `.venv` with pinned `requirements.txt`, resolved with `pip --uploaded-prior-to 2026-10-29` (releases older than 7 days, incl. transitive deps) | – |
| ENV-14 | must run offline | no CDN; all assets local |
| ENV-15 | `02_laden.sql` only runs in the Linux container (`/daten/…`, `COPY FROM PROGRAM 'gunzip'`) | own loader `python -m statagent laden` (`statagent/etl/load.py`) into the same `roh.*` tables; `01_schema.sql` runs unchanged |
| ENV-16 | ~~pinned `pytest==9.2.0` aborts on Python 3.10 before running any test~~ **resolved 2026-11-05**: `pytest<9` in requirements.in → pytest 8.4.2 (release older than 7 days); 27 tests pass | – |

## 6 Specification ambiguities (SPEC)

| ID | Issue | Proposed resolution |
| --- | --- | --- |
| SPEC-01 | the QB template says "gezählt am Stichtag", which is wrong after order 2 | adapt the wording per rule set (the template allows this) |
| SPEC-02 | orders 1 + 2 are retroactive, but the submission needs both the old-rule and the new-rule sheets | two rule-set versions, two complete series |
| SPEC-03 | order 3 uses "the latest delivery containing that day" (contrary to Z4); does "unplausible Geburtsdaten: Unbekannt" include month-13 dates? | versioned store; decide on DQ-05 and document it, or ask |
| SPEC-04 | after order 1 the sheet rows change ("Zeilen anpassen") vs "keine Zeilen umbenennen" | second sheet with the new rows |
| SPEC-05 | deadlines: SV BOX Fri 09:00 vs GitHub "bis zum Ende der Challenge"; overlapping 12:45 slots in the final round | Fri 09:00 binding for everything |
| SPEC-07 | "per Sprache": voice or text? | natural-language text is enough; voice optional |

(SPEC-06 has been merged into ENV-11.)

## 7 Not problems – real developments (RD)

These are genuine. "Correcting" them costs points. QB classification: *erklärt – plausibel*.

| ID | Development | Evidence |
| --- | --- | --- |
| RD-01 | seasonality (tourism, construction) | Gastronomie 24,542 (08/24) → 20,336 (11/24) → 24,475 (12/24) → 19,847 (04/25) → 25,086 (07/25); Tirol 35,437 → 33,779 (04/25) → 36,644 (12/25); Bau 28,858 → 23,809 (01/25) |
| RD-02 | steady decline of Beamte | 13,562 (08/24) → 12,134 (07/26) |
| RD-03 | ÖNACE 2008 → 2025 classification break | section J 12,869 rows (L2024-12) → 2,703 (L2025-01); see DQ-13 |
| RD-04 | pension law effects | PVA Schwerarbeit §607/14 ASVG → 0 (2024/25); women in §4 Abs. 3 APG 74 → 308 |
| RD-05 | carrier mergers 2020 | PEN-06 |
| RD-06 | normal late-report revisions (10 to ~700 per month) | DQ-12 |

## 8 Known bugs and limitations of StatAgent itself (SW, W)

Status 2026-11-06. Problems of our own software, not of the delivered data. **Prio:** A = should be fixed before the submission/jury · B = improves the score or robustness · C = nice to have. Frontend details: `web/STATUS.md` (W-01–W-14).

### 8.1 Open human steps (block deliverables, not bugs)

| ID | Problem | Prio | Fix |
| --- | --- | --- | --- |
| SW-01 | Change orders 1–3 had only run as rehearsals | done 06.11. | given to the agent (tasks 10–12 → R-A1/2/3), approved, carried out by the agent (task 14): 24 `auftraege` runs 218–241 (07/2026 whole month 407,604; Arbeiter/Angestellte/Beamte 147,736 / 247,579 / 12,289), 24 QBs `auftraege`, `aggregationen_auftraege.xlsx` + Open-Data-File (96 sheet-months checked), `ministerium_2026-07.csv` (32,741 persons); protocol entries 53–62; ministry delivery released 06.11. 07:30 (entry 62) |
| SW-02 | Commits lack the line `Freigegeben-von: Name`. T8 is already met by `protokoll/protokoll.md` (instruction, change, approver, time) – the commit form is only one sufficient way („reicht“). Required is only that everything is committed and pushed before 09:00 | B (push: A) | push everything; optionally empty commits per approval with `Freigegeben-von:` |
| SW-03 | No Azure access received (ENV-10) | done 06.11. | data agent runs with Anthropic `claude-sonnet-5-5` (key in `.env`, tested live); switch to Azure or any other provider at any time via `AGENT_*` in `.env`; every call logged in `ops.llm_call` |

### 8.2 Functional limitations

| ID | Problem | Prio | Fix |
| --- | --- | --- | --- |
| SW-04 | The offline parser understands documented question types and phrasings only; unusual wording → Rückfrage or „mehrdeutig“ instead of an answer | done 06.11. | live agent understands free wording (also English); offline parser extended (English months, men/women, pensions, scope gate) |
| SW-05 | No explicit feasibility check: questions about data that is not delivered (income, employer, place of residence, Teilzeit) are not always answered with „nicht verfügbar – vorhanden sind …“ | done 06.11. | `intent.UNAVAILABLE` (Einkommen, Dienstgeber, Wohnort, Arbeitszeit, Arbeitslosigkeit, Staatsbürgerschaft, Bildung, Bezirk/Gemeinde) → abstention „nicht verfügbar“ + list of what is available; „Arbeitgeber wechseln“ stays Fluktuation |
| SW-06 | Rückfrage options are not always exactly three (Fluktuation has four readings); free text in Rückfragen only keyword-matched in the UI | partly done 06.11. | every term now has exactly three readings (Fluktuation reading d removed in `sql/110`); open: backend free-text mapping for Rückfragen (UI keyword match remains) |
| SW-07 | Dynamic data-quality handling worked on record level only for Verhältnisse; for Personen and Zu-/Abgänge only „Monat ausblenden“ | done 06.11. | `quality.recompute`: Personen and Zu-/Abgänge/Fluktuation(srate) are counted again on the treated record set (official records − removed + added, copy also covers the previous months) with the official definitions; without changes it reproduces the official values exactly (tested); e.g. DQ-02 carried forward: Abgänge 10/2025 91,536 → 14,026, Zugänge 11/2025 88,155 → 14,901 |
| SW-08 | Free text for the data-quality handling is mapped by keywords (or by the model, if configured); anything else is only stored as a note, never executed | C | by design (no LLM-written logic); could create a Rückfrage or rule proposal from the note |
| SW-09 | The monthly report in the layout of `beispielbericht_2024-08.xlsx` (Deckblatt, Tab1–Tab13) is not generated; it is only used for the calibration | C | generator from the calibration code (all cells are already computed) |
| SW-10 | Calibration showed „nicht bestanden“: 359 cells of Tab13 differ because the approved R-DQ05 swaps day/month while the example report used the birth year | done 06.11. | calibration also computes the example report's reading for the 370 month-13 birth dates (age = year − birth year, nothing stored): 0 differences → status „bestanden – Abweichungen vollständig durch R-DQ05 erklärt“; both variants in `abgabe/kalibrierung_2024-08.md`, exit code 0 |
| SW-11 | R-DQ05 can swap only where the day is ≤ 12 (08/2024: 143 of 370); the rest falls back to „Alter unbekannt“; a swapped date can yield implausible ages (one 14-year-old in 08/2024) | C | parameter `fallback: jahr`, or plausibility check of swapped dates |
| SW-12 | Generated code (Sonderauswertungen) only from a fixed template: groupings/filters on age bands, Wien/Rest, categories, sex, Bundesland, ÖNACE; no arbitrary new logic; path approve → execute never run end to end with a real approval | B | rehearse once with a real approval before the jury (C-proposal via Agent, approve, „Setze … um“) |
| SW-13 | Agent `execute_approved` runs all 24 `auftraege` months inside one SSE request (~20 min); a closed browser tab does not stop it, progress is only visible while connected | B | run as background job with status in `ops.run`, resumable view in „Läufe“ |
| SW-14 | Only one job at a time in the API (job lock); a second run/preview reports „Es läuft bereits ein anderer Auftrag“ | C | queue |
| SW-15 | Published months are frozen (Z4): changing an approved rule later requires a new rule set or a revision procedure, not a rerun | C | by design; a „Revision“ workflow could be added |
| SW-16 | DQ-16 phantom double registrations are counted as delivered in the official series (as in the example report); exclusion only per statistic in the chat | C | Rückfrage RF-DQ16 answer → rule |
| SW-17 | Models (corridor/detector) evaluated on only one real delivery per error type; seasonality calibrated on the same 24 deliveries that are used for evaluation; corridor works on „wie geliefert“ values (W-06) | C | honest limits in MODELLE.md; more history needed |
| SW-18 | Pension statistic: year-over-year jumps of LZV (women, 2019) classified „nicht erklärbar“; no pension QB per year, only one Prüfbericht | C | Rückfrage to the Fachabteilung |

### 8.3 Technical issues

| ID | Problem | Prio | Fix |
| --- | --- | --- | --- |
| SW-19 | The database is local and not in git (10 GB; GitHub allows 100 MB per file) | done 06.11. | `statagent sichern` → compressed dump `sicherung/*.dump` (0.51 GB, ~3 min) + SHA-256, `wiederherstellen DATEI --ja` (checks SHA-256, pg_restore, ANALYZE); share the dump outside git (USB, SV-Box, release asset ≤ 2 GB); `sicherung/` is git-ignored. Dump verified readable end to end (56 tables); a test restore into a second database needs CREATEDB rights the user `statistik` does not have |
| SW-20 | No real authentication: login = typed name (W-08); anyone with local access can approve under any real name; the API is bound to 127.0.0.1 only | B (for production) | acceptable for the challenge; production needs SSO and roles |
| SW-21 | The answer log `ops.answer` and `work.dq_copy` contain development test entries (users „Test“, „Smoke Test“, „Probe Tester“) | done 06.11. | deleted: 95 test answers, 25 test choices, 326,933 copy rows, 1 test agent task (approvals and protocol untouched) |
| SW-22 | `work.dq_copy` grows with every recalculation in the chat (no cleanup) | done 06.11. | `quality.apply` deletes copies older than `COPY_DAYS` = 7; the choices in `ops.dq_choice` stay as audit trail |
| SW-29 | Links between pages were missing (Lieferungen month/run/file, Quellennachweis, Protokoll objects, QB run/rules) | done 06.11. | Lieferungen: month → QB, hash → Dateiregister, run → `/laeufe?lauf=`; `?monat`/`?ansicht`/`?q` in the URL; Läufe opens `?lauf=`; evidence panel links deliveries, runs, rules; Protokoll `rule:`/`month:` objects; QB run/Lieferung/rule IDs |
| SW-30 | Web feedback 06.11.: Modelle detector table hard to read; „basis“/„auftraege“ shown raw; Ministeriums-Lieferung button errored without approved R-A3; Qualitätsberichte list took 18 s; chart switcher always offered the same three kinds; approvals by „Test User“ were accepted | done 06.11. | detector scorecard per error type (precision/recall bars, found/false alarms); labels „Basis“/„Aufträge“ (values unchanged); ministry button only with approved rule + explanation; QB list query 18 s → 0.24 s; only sensible chart kinds (years = time axis → line); curated example questions (`sql/120`); approver names with Test/Probe/Demo/Gast/User rejected; change-order execution resumes after a crash (months computed after the last approval are kept); Fragen logged as `STATAGENT_FRAGEN_PERSON` (Mercy) when nobody is logged in; Excel computes „Insgesamt“ on opening (`fullCalcOnLoad`) |
| SW-31 | Pensionen page hard to read (run line and long note under the header, all carrier names in one sentence, flat-looking series on a shared axis, total bar hiding the small kinds, transition graph drawn 2020 → 2019 with edges pointing outwards); run chips not clickable; Agent page had no hint how to carry out approved orders and the offline parser did not recognise „Setze die freigegebenen Aufträge um“; Ministry file from Exporte not in the protocol | done 06.11. | header lines removed, break note on hover of „Bruch 2020 ⓘ“ (instant HTML tooltip), carrier names on hover (legend + description), „Entwicklung je Reihe“ small multiples with own axes (default) next to „Vergleich auf einer Achse“, total as KPI, short bar labels, graph columns 2018–2019 → 2020–2025 with a precise description and a styled transition list, Tabelle 13 legend in the highlight colour; run chips link to `/laeufe?lauf=` (non-month runs show kind, values, note); Agent templates (Auftrag 1–3, „Freigegebene Aufträge umsetzen“, Sonderauswertung) + deterministic `execute` intent; Exporte ministry generation logged in `ops.change_log` |
| SW-32 | `coordinator.handle` ran a whole order on one non-autocommit connection: the per-month `conn.transaction()` was only a savepoint, so nothing was committed before the end and the resume after a crash could not take effect | done 06.11. | `execute_approved(..., commit_each=not dry_run)` commits the classification level and every finished month; dry runs stay one rolled-back transaction |
| SW-23 | API auto-reload does not detect changes on this Windows machine; after backend changes the API must be restarted by hand | C | restart `statagent web` (or install `watchfiles`) |
| SW-24 | Full runs are slow on this laptop: `bestand` ~4 min, `gesamtlauf` ~15–20 min (quality checks and revisions per month); the first run of a new rule set needed statistics fixes (ANALYZE, hash joins) | C | fine for the challenge; partitioning of `store.segment` per delivery would help |
| SW-25 | `/api/annahmen` and long chat questions over a year take 2–9 s (W-13) | C | precomputed hits per rule and month |
| SW-26 | psql on Windows breaks on umlauts (console codepage); shell heredocs in this environment lose backslash escapes (development note) | C | use `scratchpad/q.py`-style Python queries; Write/Edit tools for code |
| SW-27 | Tests: integration tests need the local DB and take ~6 min; no frontend tests | done 06.11. | 45 tests; `pytest -m "not integration"` runs the 28 unit tests in < 1 s; frontend smoke test `pnpm test:smoke` (`web/scripts/smoke.mjs`, no extra package: headless Edge via DevTools protocol, 15 pages + links, `--frage` asks one live question) |
| SW-28 | Frontend: chart animations disabled (W-04), dev server sometimes serves stale modules (W-03), Exporte uses `window.confirm` (W-11), pinned cards are snapshots (W-07) | done 06.11. (W-03 stays) | W-04: charts fade/rise in with CSS (Recharts animations stay off – they never finished on the dashboard); W-11: styled confirmation dialog with file, SHA-256 and name; W-07: „Aktualisieren“ on pinned cards re-asks with the same parameters; W-03 is a Next dev-server quirk (restart `pnpm dev`) |
