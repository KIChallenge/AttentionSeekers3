# References – papers, standards and open-source software relevant to StatAgent

Prior art and standards we build on or align with, grouped by PRD section. **Use** = we can build on it (Python, licence suitable as a dependency). **Cite** = reference for the approach, metrics or standard only (R, unsuitable licence, or no dependency needed). Phase numbers refer to [Phases.md](../Phases.md); rule and problem IDs to [StateOfDevelopment.md](../StateOfDevelopment.md) and [Problems.md](../Problems.md).

## 1 Process framing (five steps, quality report)

| Source | What it is | Relevance | Use/Cite |
| --- | --- | --- | --- |
| UNECE **GSBPM 5.1**; Eurostat CROS, [Validation and the GSBPM](https://cros.ec.europa.eu/book-page/validation-and-gsbpm) | Standard model of a statistical production process: validation in 4.3 (file/structure) and 5.3 "Review and validate", changes in 5.4 "Edit and impute" | Maps our steps to the official vocabulary: `laden`/`pruefen` = 4.3, store + QA checks = 5.3, reading rules = 5.4 – with the difference that we never write back, we interpret at read time | Cite |
| Di Zio et al., [Methodology for data validation](https://www.markvanderloo.eu/files/share/zio2015methodology.pdf) (ESS handbook); Eurostat [Data validation](https://ec.europa.eu/eurostat/data/data-validation) | Validation levels 0–5: file structure → within a dataset → across datasets of one source → … | Our checks map 1:1: level 0 = checksums and row counts, level 1 = DQ-01/03/05–11 within a delivery, level 2 = DQ-02/04/12/16 against earlier deliveries; structure for the QB table "Auffälligkeiten" | Cite |
| UNECE HLG-MOS, [White paper on generative AI for official statistics](https://unece.org/sites/default/files/2023-11/HLG2023%20LLM%20Paper.pdf) (Dec 2023) | Position of the NSI community on LLMs: drafting, coding, retrieval – numbers come from the production system | Backs T1 and our no-hallucination principle with the sector's own guidance | Cite |
| ONS Data Science Campus, [StatsChat](https://datasciencecampus.ons.gov.uk/using-large-language-models-llms-to-improve-website-search-experience-with-statschat/) (open source, 2023); Statistics Canada [AI Adoption Roadmap](https://unstats.un.org/bigdata/events/2025/ai-data-science/webinar2/presentations/Wesley_STC%20AI%20Adoption%20Roadmap%20-%20Dec%202024.pdf) | NSI chatbots where the LLM only retrieves and points to published text; ONS paused StatsChat over reputational risk | Argument for our design: the agent selects and renders, never states numbers; claim check before display | Cite |
| [SNStatComp/awesome-official-statistics-software](https://github.com/SNStatComp/awesome-official-statistics-software) | Curated open-source tools used by NSIs, organised by GSBPM phase | Shows our choices come from what NSIs use (VTL engines, validate, SDMX tools) | Cite |

## 2 Rules as data (T3) and validation

| Source | What it is | Relevance | Use/Cite |
| --- | --- | --- | --- |
| **VTL 2.1** (SDMX Validation and Transformation Language); engines [InseeFr/Trevas](https://github.com/InseeFr/Trevas) (Java, MIT), [Meaningful-Data/vtlengine](https://github.com/Meaningful-Data/vtlengine) (Python, AGPL-3.0), [vpinna80/VTL](https://github.com/vpinna80/VTL) (Bank of Italy, EUPL-1.2) | ESS standard for validation and transformation rules as technology-neutral, readable metadata | Exactly T3: our `ops.rule` (rule = data with parameters, code implements the action) follows the VTL philosophy; possible export format for rules later | Cite |
| `validate` and `errorlocate` (R, Statistics Netherlands; van der Loo & de Jonge, *Data Validation Infrastructure for R*, JSS 2021; Fellegi & Holt 1976); example of use at NASS: [Rule-Based Data Validation and Reconciliation](http://www.asasrms.org/Proceedings/y2024/files/Rule-Based%20Data%20Validation.pdf) | Rule-based validation infrastructure and automatic error localisation (minimal set of fields to change so that all rules hold) | Reference implementation of "rules as data" in NSIs; error localisation is the classic answer to "which field is wrong" (DQ-01 swapped columns, DQ-09 overlaps) | Cite |
| [Great Expectations](https://github.com/great-expectations/great_expectations) (Apache-2.0), [pandera](https://github.com/unionai-oss/pandera) (MIT) | Declarative data expectations with generated documentation; schema-as-code for dataframes (pandera also synthesises rows from a schema) | Candidate for level-0/1 checks with auto-generated check docs; our SQL checks already cover this, kept as the considered alternative | Use (optional) |

## 3 Error detection, selective editing, synthetic errors (Phase 3b – error detector)

| Source | What it is | Relevance | Use/Cite |
| --- | --- | --- | --- |
| **Raha & Baran**, [BigDaMa/raha](https://github.com/BigDaMa/raha) (Apache-2.0); Mahdavi et al., SIGMOD 2019 / VLDB 2020 | Configuration-free error detection and correction: many base detectors propose candidates, a semi-supervised ensemble learns from a few user labels; transfer learning from historical datasets | Closest precedent to our detector: ensemble of cheap detectors + human labels + learning across deliveries ("flag, let a person confirm, learn the rule") | Use/Cite |
| **Jenga**, [schelterlabs/jenga](https://github.com/schelterlabs/jenga); Schelter et al., [EDBT 2021](https://openproceedings.org/2021/conf/edbt/p134.pdf) | Library that injects realistic data corruptions (missing values, swapped or scaled values, typos, encodings) with controlled intensity | Blueprint for planting labelled errors in our synthetic deliveries; our corruptions are domain-specific (swapped BEGINN/ENDE, 20 % drop, phantom VVH, month 13) | Use (pattern) |
| **HoloClean**, Rekatsinas et al., VLDB 2017 | Probabilistic repair combining constraints, statistics and external data | The "automatic repair" family we deliberately do not adopt: Anhang A requires documented assumptions and human approval | Cite |
| **SeleMix** (Istat, R; [vignette](https://www.istat.it/wp-content/uploads/2023/12/SeleMix-vignette.pdf)); selective/significance editing (Lawrence & McKenzie 2000) | Prioritise records by risk × influence on the published estimate | Justifies our severity scale (DQ-02/04 high, DQ-14/17 low) as a selective-editing argument | Cite |

## 4 Expected corridor and forecasting (Phase 3b – corridor)

| Source | What it is | Relevance | Use/Cite |
| --- | --- | --- | --- |
| [sktime](https://www.sktime.net/) (BSD-3), [Darts](https://unit8co.github.io/darts/) (Apache-2.0) | Unified forecasting APIs: ETS, SARIMA, Theta, probabilistic intervals, backtesting; Darts adds conformal prediction and hierarchical reconciliation | Seasonal baseline per series with intervals; reconciliation keeps Bundesland/ÖNACE corridors adding up to the total; deterministic with seeds, offline | Use |
| [Merlion](https://opensource.salesforce.com/Merlion/) (Salesforce, BSD-3) | Forecast-based anomaly detection: anomaly score = deviation from forecast ± uncertainty | The "outside corridor = suspected error" mechanism | Cite (pattern) |
| [MAPIE](https://mapie.readthedocs.io/) (scikit-learn-contrib, BSD-3) – EnbPI/ACI for time series | Conformal prediction intervals with coverage guarantees, adaptive to drift | Calibrated corridor widths from synthetic residuals; gives an honest coverage figure for the model card | Use |
| X-13ARIMA-SEATS (US Census Bureau), JDemetra+ (Eurostat) | Official seasonal adjustment used by NSIs | Clarifies that our corridor is a QA device, not seasonal adjustment; seasonality (RD-01) is expected, not an error | Cite |

## 5 Synthetic data generation (Phase 3b – generator)

| Source | What it is | Relevance | Use/Cite |
| --- | --- | --- | --- |
| **synthpop** (R, GPL-2/3); Nowok, Raab & Dibben, [JSS 2016](https://www.jstatsoft.org/article/view/v074i11); [UNECE 2015](https://unece.org/fileadmin/DAM/stats/documents/ece/ces/ge.46/20150/Paper_24_bnowok_synthpop.pdf) | Sequential conditional synthesis (CART/parametric) of microdata for NSIs with utility and disclosure metrics | NSI-standard reference for synthetic microdata; utility evaluation (marginals and relationships synthetic vs. real) frames our generator's acceptance test | Cite |
| [SDV](https://github.com/sdv-dev/SDV) / [DeepEcho PAR](https://github.com/sdv-dev/DeepEcho) (**Business Source License** – not as a dependency); [SDMetrics](https://github.com/sdv-dev/SDMetrics) (MIT); [Sequential Models in the SDV](https://arxiv.org/abs/2207.14406) | Generators for tabular and multi-sequence data; metrics to score synthetic vs. real | Prior art; SDMetrics' quality report idea is useful. Our generator stays a calibrated simulation of VVH lifecycles: simpler and fully deterministic | Cite |
| **medlyn**, [Julian-AT/medlyn](https://github.com/Julian-AT/medlyn) (CC BY-NC 4.0, used with permission) | 100k synthetic patients, own QLoRA verifier, separate evaluation populations, model card; source-linked facts, proven absence, contradictions shown side by side | The pattern we mirror: generate → train → evaluate on held-out synthetic **and** real data → honest metrics; UI styling and the "Quellennachweis" idea | Cite |

## 6 No hallucination, source-linked answers, verified text-to-SQL (Phases 4–5)

| Source | What it is | Relevance | Use/Cite |
| --- | --- | --- | --- |
| Alrashed et al., [Developing and Benchmarking Verification Algorithms to Improve Text-to-SQL Generation](https://www.vldb.org/pvldb/vol19/p3732-alrashed.pdf) (PVLDB 19, 2026) | Verification as its own task: round-trip critique (SQL → NL) and synthetic execution consistency; **selective generation** = abstain when unsure | Our claim check for data questions: verify the SQL against the question and answer „nicht eindeutig“/„nicht vorhanden“ instead of guessing | Use (pattern) |
| [TA-SQL, "Before Generation, Align it!"](https://arxiv.org/abs/2405.15307) (2024); DIN-SQL, DAIL-SQL; **BIRD** and **Spider** benchmarks; [Noise in BIRD-Bench](https://arxiv.org/abs/2402.12243) (2024); [FLEX](https://arxiv.org/abs/2409.19014) | Hallucination taxonomy per text-to-SQL stage (schema linking, logic); benchmarks and their label noise | Failure modes we guard against (wrong table or version, wrong Stichtag semantics) and why we always show SQL + definition | Cite |
| Dhuliawala et al., [Chain-of-Verification Reduces Hallucination in LLMs](https://aclanthology.org/2024.findings-acl.212/) (ACL Findings 2024) | Draft → plan verification questions → answer independently → revise | General technique; our variant is stricter: verification is deterministic (query results), not another LLM pass | Cite |
| LangGraph [interrupts / human-in-the-loop](https://docs.langchain.com/oss/python/langgraph/interrupts) | Pause an agent before a critical action, persist state, resume after approval or edit | Reference pattern for the T6/T7 approval gate (rule change, run, delivery); implemented in our thin orchestrator without the dependency | Cite (pattern) |

## 7 Classifications and transitions (Phase 2)

| Source | What it is | Relevance | Use/Cite |
| --- | --- | --- | --- |
| Eurostat NACE [correspondence tables](https://ec.europa.eu/eurostat/web/nace/correspondence-tables) and [transition guidance](https://ec.europa.eu/eurostat/web/nace/transition) (Rev. 2 → Rev. 2.1: backcasting, parallel series, double reporting) | Official handling of the classification break that ÖNACE 2025 implements | Backs DQ-13/RD-03: break footnote, comparison via `klass_uebergang` with shares, no "correction" of the jump | Cite |
| Statistik Austria [Klassifikationsdatenbank](https://www.statistik.at/en/databases/classification-database) | Source of the ÖNACE files (structure, explanatory notes, Umsteiger) | Provenance of `klass_oenace` | Cite |
| [rakoort/spore-nace](https://github.com/rakoort/spore-nace) (TypeScript) | Vendored Eurostat correspondence; resolves only to the level the source code determines | Same principle as our derived section transitions: never claim a finer code than the data supports | Cite |
| SDMX / GSIM | Standards for statistical metadata: code lists, versions, correspondences | Our `klass_*` / Übergänge / Quellzuordnung model is Anhang B, and SDMX-compatible in spirit (code list + version + correspondence) | Cite |

## Licence summary for dependencies

- Suitable as dependencies (BSD/MIT/Apache): sktime, Darts, MAPIE, scikit-learn, Great Expectations, pandera, Merlion, Raha.
- Cite only: synthpop, validate, errorlocate, SeleMix (R, GPL); SDV/DeepEcho (Business Source License); vtlengine (AGPL-3.0); medlyn styling (CC BY-NC 4.0, with the author's permission; commercial use needs a separate licence).
- Any new dependency is added only as a release older than 7 days (AGENTS.md).
