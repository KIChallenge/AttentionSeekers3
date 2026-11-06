-- Operations: rules as data (T3), approvals by named persons (T7), change log (T8), runs, QA findings.
-- Texts shown to users (titles, descriptions, justifications) are German domain content; names are English.
CREATE SCHEMA IF NOT EXISTS ops;

-- Reading, check, counting and mapping rules. Code implements the 'action'; parameters are data.
-- Only rules with status 'approved' are applied.
CREATE TABLE IF NOT EXISTS ops.rule (
  rule_id        text PRIMARY KEY,               -- e.g. 'R-DQ01'
  problem_id     text,                           -- Problems.md ID, e.g. 'DQ-01'
  type           text NOT NULL CHECK (type IN ('reading', 'check', 'counting', 'mapping')),
  title          text NOT NULL,                  -- German, shown in the UI
  description    text NOT NULL,                  -- what the rule does
  assumption     text,
  justification  text,
  action         text NOT NULL,                  -- action implemented in code, e.g. 'swap_columns'
  parameters     jsonb NOT NULL DEFAULT '{}',
  rule_set       text NOT NULL DEFAULT 'basis',  -- 'basis' = Fachbeschreibung rules; later: after the change orders
  status         text NOT NULL DEFAULT 'proposed'
                 CHECK (status IN ('proposed', 'approved', 'rejected', 'retired')),
  created_by     text NOT NULL,
  created_at     timestamptz NOT NULL DEFAULT now(),
  approved_by    text,
  approved_at    timestamptz
);

-- Every approval decision: who, when, what (rule, code file or delivery). No placeholders like "Team".
CREATE TABLE IF NOT EXISTS ops.approval (
  approval_id  bigserial PRIMARY KEY,
  object_type  text NOT NULL CHECK (object_type IN ('rule', 'code', 'delivery')),
  object_id    text NOT NULL,
  decision     text NOT NULL CHECK (decision IN ('approved', 'rejected')),
  person       text NOT NULL CHECK (length(trim(person)) > 2
                 AND lower(trim(person)) NOT IN ('team', 'admin', 'agent', 'statagent', 'system', 'user', 'test')),
  decided_at   timestamptz NOT NULL DEFAULT now(),
  comment      text
);

-- Change log (T8): instruction, change, approver; git commit added in Phase 5.
CREATE TABLE IF NOT EXISTS ops.change_log (
  log_id       bigserial PRIMARY KEY,
  logged_at    timestamptz NOT NULL DEFAULT now(),
  instruction  text,                             -- natural-language instruction, if any
  change       text NOT NULL,                    -- what was changed (German, shown in the protocol)
  object       text,                             -- e.g. 'rule:R-DQ01'
  approved_by  text,
  git_commit   text
);

-- Runs: store builds ('store'), monthly production runs ('month') and classification builds ('classification').
CREATE TABLE IF NOT EXISTS ops.run (
  run_id       bigserial PRIMARY KEY,
  kind         text NOT NULL CHECK (kind IN ('store', 'month', 'classification')),
  delivery     text,                             -- JJJJ-MM; NULL = all deliveries
  rule_set     text NOT NULL DEFAULT 'basis',
  rules        text[] NOT NULL DEFAULT '{}',     -- approved rules applied in this run
  started_at   timestamptz NOT NULL DEFAULT now(),
  finished_at  timestamptz,
  status       text NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'done', 'failed')),
  row_count    bigint,
  checksum     text,                             -- reproducibility (T1)
  note         text
);

-- QA findings per delivery (filled from Phase 3 on; template: vorlagen/qualitaetsbericht_vorlage.md).
CREATE TABLE IF NOT EXISTS ops.finding (
  finding_id      bigserial PRIMARY KEY,
  run_id          bigint REFERENCES ops.run,
  delivery        text NOT NULL,
  problem_id      text,
  level           text NOT NULL CHECK (level IN ('record', 'aggregate', 'delivery')),
  description     text NOT NULL,
  extent          bigint,
  example_ids     text[],
  evidence_sql    text,
  classification  text CHECK (classification IN ('explained_plausible', 'explained_data_problem', 'unexplained')),
  measure         text,
  rule_id         text REFERENCES ops.rule,
  inquiry_id      text
);

-- Queries to the Fachabteilung (template: vorlagen/rueckfrage_vorlage.md); answers become rules.
CREATE TABLE IF NOT EXISTS ops.inquiry (
  inquiry_id           text PRIMARY KEY,         -- R1, R2, …
  delivery             text NOT NULL,
  problem_id           text,
  question             text NOT NULL,
  proposal             text,
  extent               bigint,
  example_ids          text[],
  evidence_sql         text,
  asked_on             date,
  answer               text,
  answered_on          date,
  implemented_as_rule  text REFERENCES ops.rule
);
