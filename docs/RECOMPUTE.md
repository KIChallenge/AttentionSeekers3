# Recompute after the rule approvals (2026-11-05/06)

What the seven commands of the night of 5 → 6 November did, why they were necessary, and what came out. All numbers below are read from the database after the run.

## Why it was necessary

Approving a rule (`freigeben`) only records a decision: who, when, why. It does **not** change any number. All results that existed before – the versioned store, the 24 monthly values in `stat_beschaeftigte`, the 24 quality reports and the Aggregations-Sheet – had been computed **before** R-DQ03, R-DQ05 and R-DQ09 were approved, i.e. without them. To make the official results follow the approved rules, everything that depends on them had to be rebuilt in order. The delivered files themselves are never touched (they are only read again).

Approved by Mercy on 05.11.2026 23:19–23:20: **R-DQ03** (exact duplicates count once), **R-DQ05** (birth month 13 = wrong date format, day and month read swapped where possible), **R-DQ09** (overlapping segments: the later one wins from its start). Not approved, by team decision: R-DQ02, R-DQ04, R-DQ10 – these problems are handled per statistic in the chat instead (three options + free text on a copy of the affected records).

## The seven commands

| # | Command | What it did | Why | Result |
| --- | --- | --- | --- | --- |
| 1 | `bestand` | Re-read all 10,152,292 delivered records (24 deliveries) into the versioned store `store.segment`, applying the approved **reading rules** – now including R-DQ03 (duplicate copies marked as not counted) and R-DQ09 (an overlapping segment ends the day before the next one). | R-DQ03 and R-DQ09 act on the record level, so the store – the basis of every monthly run – had to be rebuilt first. | store run done 05.11. 23:53; all rows kept (nothing deleted, copies only marked) |
| 2 | `gesamtlauf` | 24 monthly runs in order (2024-08 … 2026-07): counting rules Z1–Z8 on the Stichtag, codes via the approved source mappings, age now with R-DQ05, gates (every VVH counted exactly once, reconciliation), findings, revision need, Rückfragen and one **quality report** per month. | Each month must be produced from its own delivery with the rules valid now; months run in order because each compares with the earlier ones. | runs 148–171; 24 QBs in `abgabe/qualitaetsberichte/basis/` listing R-DQ01/03/05/07/08/09 with approver |
| 3 | `kalibrierung` | Recomputed all 2,880 cells of `beispielbericht_2024-08.xlsx` from the new 08/2024 result. | Checks the production against the official example. | totals and Tab1–Tab12 match (392,236); **359 cells of Tab13 (age) differ** – expected: the example report used age = year − birth year for month-13 dates, R-DQ05 swaps day and month instead. Since 06.11. the calibration proves it: read like the example report all 2,880 cells match → „bestanden – Abweichungen vollständig durch R-DQ05 erklärt“ |
| 4 | `veroeffentlichen --von … --regelwerk basis` | Set all 24 months to **endgültig** with a named approval per month (24 entries in `ops.approval`, logged in the protocol). | The task requires the statistic "nach den bisherigen Regeln" to be final before the change orders; published months are frozen (Zählregel Z4) – later differences only appear as revision need. | all 24 months `endgueltig`, approved by Mercy 06.11. 00:22 |
| 5 | `aggregationen --regelwerk basis` | Filled `vorlagen/aggregationen_vorlage.xlsx` with the final numbers and wrote the Open-Data-File; refuses if any sheet-month differs from `stat_beschaeftigte`. | Mandatory deliverable, must show the final values. | `abgabe/aggregationen_basis.xlsx`, `abgabe/stat_beschaeftigte_basis.csv.gz` (06.11. 00:27) |
| 6 | `protokoll` | Exported `ops.change_log` to `protokoll/protokoll.md` and printed the suggested commit message. | T8: every change with instruction, approver, time; the team commits. | 31 protocol entries |
| 7 | `pruefen`, `geheimnisse` | Re-checked the SHA-256 of all 115 package files and the 10,152,292 rows; scanned git history and files for secrets. | Proof that no delivered file changed and no credential is in the public repo. | OK / 0 findings |

## What changed in the numbers

| Month | before | after | Cause |
| --- | ---: | ---: | --- |
| 2024-09 | 393,454 | 393,453 | R-DQ09: VVH 56000 has an open segment followed by a one-day segment ending 31.08.2024; the open one now ends before the next starts, so it no longer counts on 30.09.2024 (predicted by the preview, Problems.md DQ-11) |
| all other months | – | unchanged | R-DQ03 does not change counts (each VVH was already counted once); R-DQ05 moves 336–444 VVH per month from „Alter unbekannt“ to an age (where the day is ≤ 12) and keeps the rest as unknown – totals unchanged |

10/2025 stays at 313,154 (as delivered): R-DQ02 is not approved; the quality report says so and Rückfrage RF-DQ02 is open. Users can recompute it with carry-forward in the chat (≈ 390,664, labelled „keine amtliche Zahl“).

## What it means for the rest

- The basis series is now **final and frozen**. A rerun with the same rules reproduces the same checksums; a rerun with different rules is refused for published months.
- Afterwards (06.11. 06:54–07:15) the change orders 1–3 were carried out through the agents (`docs/RUNBOOK.md` §3): second series `auftraege`, its sheet and QBs, and `ministerium_2026-07.csv`.
- Commits: the last commit (`982ed8e`) contains the approvals; for rule T8 each approval commit should end with a line `Freigegeben-von: Name` (see the suggested message of `protokoll`).

## Reproducing it after a fresh clone

The database is local and not in git. `protokoll` now also writes `protokoll/freigaben.json` (all rule decisions with person, time, comment and a fingerprint of the approved rule). Faster: copy a dump from `statagent sichern` (0.5 GB, outside git) and run `statagent wiederherstellen DATEI --ja`, then `pruefen`. Without a dump, in a fresh clone run `migrieren → laden → pruefen → freigaben-wiederherstellen → klassifikation → bestand → gesamtlauf → kalibrierung → aggregationen`: the same approved rules give the same checksums per month. A rule whose text/parameters changed is not restored and needs a new approval; publishing again is a decision by a person.
