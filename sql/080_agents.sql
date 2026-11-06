-- Phase 4/5 – agents, chat answers, claim check, code proposals (T6), ambiguity catalogue and suggestions (PRD §5.3, §5.4).

-- Every LLM call (model and deployment logged per call, T4).
CREATE TABLE IF NOT EXISTS ops.llm_call (
  call_id     bigserial PRIMARY KEY,
  called_at   timestamptz NOT NULL DEFAULT now(),
  deployment  text, model text, purpose text,
  tokens_in   integer, tokens_out integer, seconds numeric, error text
);

-- Answer log: question, interpretation, tool calls, result hash, claim check, model, rendered text.
CREATE TABLE IF NOT EXISTS ops.answer (
  answer_id       bigserial PRIMARY KEY,
  asked_at        timestamptz NOT NULL DEFAULT now(),
  "user"          text,
  role            text,
  conversation    text,
  question        text NOT NULL,
  interpretation  jsonb,
  tool_calls      jsonb,
  result_hash     text,
  claim_check     jsonb,
  model           text,
  text            text,
  kind            text                          -- answer | clarification | abstention | metadata | error
);

-- Ambiguity catalogue: terms with several defensible readings -> Rückfrage (PRD §5.3). Extendable by the Fachabteilung.
CREATE TABLE IF NOT EXISTS ops.term (
  term           text NOT NULL,
  reading_id     text NOT NULL,
  label_de       text NOT NULL,
  definition_de  text NOT NULL,
  params         jsonb NOT NULL DEFAULT '{}',   -- tool parameters this reading sets (measure, rule set, ...)
  is_default     boolean NOT NULL DEFAULT false,
  always_ask     boolean NOT NULL DEFAULT false,
  sort           integer NOT NULL DEFAULT 0,
  PRIMARY KEY (term, reading_id)
);

-- Suggested questions ("Beispielfragen", PRD §5.4): fill the input, never submit.
CREATE TABLE IF NOT EXISTS ops.prompt_suggestion (
  suggestion_id  serial PRIMARY KEY,
  text_de        text NOT NULL UNIQUE,
  role           text NOT NULL DEFAULT 'alle',
  sort           integer NOT NULL DEFAULT 0,
  active         boolean NOT NULL DEFAULT true
);

-- Code written by agents (T6): readable file in statagent/generated/, approved before its first run, every run logged.
CREATE TABLE IF NOT EXISTS ops.code_proposal (
  proposal_id   text PRIMARY KEY,               -- e.g. 'C-0001'
  created_at    timestamptz NOT NULL DEFAULT now(),
  created_by    text NOT NULL,                  -- agent role, e.g. 'Agent Reporting'
  instruction   text NOT NULL,                  -- natural-language instruction
  path          text NOT NULL,                  -- relative path of the generated file
  sha256        text NOT NULL,                  -- the approved content is pinned by its hash
  description   text NOT NULL,
  params        jsonb NOT NULL DEFAULT '{}',
  status        text NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed', 'approved', 'rejected', 'retired')),
  approved_by   text,
  approved_at   timestamptz
);
CREATE TABLE IF NOT EXISTS ops.code_execution (
  execution_id  bigserial PRIMARY KEY,
  proposal_id   text NOT NULL REFERENCES ops.code_proposal,
  started_at    timestamptz NOT NULL DEFAULT now(),
  finished_at   timestamptz,
  started_by    text,
  sha256        text NOT NULL,
  status        text NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'done', 'failed', 'blocked')),
  result        jsonb,
  output_path   text
);

-- Agent conversations: instruction -> routing -> proposals (the coordinator's work log).
CREATE TABLE IF NOT EXISTS ops.agent_task (
  task_id      bigserial PRIMARY KEY,
  created_at   timestamptz NOT NULL DEFAULT now(),
  "user"       text,
  instruction  text NOT NULL,
  role         text,                            -- Datenmanagement | Klassifikation | Qualitätssicherung | Reporting
  plan         jsonb,
  proposals    text[] NOT NULL DEFAULT '{}',    -- rule or code proposals created
  status       text NOT NULL DEFAULT 'open',
  model        text,
  log          jsonb NOT NULL DEFAULT '[]'
);

-- Read-only access for SQL issued on behalf of agents and the chat (PRD §5.1): enforced by PostgreSQL through
-- connections with default_transaction_read_only = on (statagent.config.connect_readonly). An additional reader role
-- is created only if the database user may create roles.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'statagent_reader') THEN
    BEGIN
      CREATE ROLE statagent_reader NOLOGIN;
    EXCEPTION WHEN insufficient_privilege THEN
      RAISE NOTICE 'role statagent_reader not created (no CREATEROLE); read-only connections are used instead';
    END;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'statagent_reader') THEN
    GRANT USAGE ON SCHEMA public, store, ops, roh, klassifikation TO statagent_reader;
    GRANT SELECT ON ALL TABLES IN SCHEMA public, store, roh, klassifikation TO statagent_reader;
  END IF;
END $$;

INSERT INTO ops.term (term, reading_id, label_de, definition_de, params, is_default, always_ask, sort) VALUES
('fluktuation', 'a', 'Zu- und Abgänge', 'Zugänge + Abgänge an Versicherungsverhältnissen im Monat (gegenüber dem Vormonat).', '{"measure": "fluktuation"}', false, true, 1),
('fluktuation', 'b', 'nur Abgänge', 'Beendete Verhältnisse: am Ende des Vormonats gezählt, im Berichtsmonat nicht mehr.', '{"measure": "abgaenge"}', false, true, 2),
('fluktuation', 'c', 'Fluktuationsrate', 'Abgänge ÷ Bestand am Ende des Vormonats, in Prozent.', '{"measure": "fluktuationsrate"}', false, true, 3),
('fluktuation', 'd', 'Wechsel von Personen', 'Personen, die den Dienstgeber oder Wirtschaftszweig wechseln – nicht bestimmbar: die Lieferungen enthalten keine Dienstgeber-ID.', '{"unavailable": true}', false, true, 4),
('beschaeftigte', 'vvh', 'Versicherungsverhältnisse', 'Zählregel Z1: Verhältnisse, nicht Personen; eine Person mit zwei Verhältnissen zählt zweimal.', '{"measure": "bestand"}', true, false, 1),
('beschaeftigte', 'personen', 'Personen', 'Jede PERSON_ID einmal, unabhängig von der Zahl ihrer Verhältnisse.', '{"measure": "personen"}', false, false, 2),
('monat', 'stichtag', 'Stichtag Monatsletzter', 'Regelwerk basis: Verhältnisse, die am Monatsletzten bestehen (Fachbeschreibung Z2).', '{"rule_set": "basis"}', true, false, 1),
('monat', 'ganzes_monat', 'ganzes Monat', 'Regelwerk auftraege: Verhältnisse mit mindestens einem Tag im Monat (Änderungsauftrag 2).', '{"rule_set": "auftraege"}', false, false, 2)
ON CONFLICT DO NOTHING;

INSERT INTO ops.prompt_suggestion (text_de, role, sort) VALUES
('Zeitreihe der Beschäftigten 08/2024 bis 07/2026', 'alle', 1),
('Wie viele Männer und Frauen waren im Juli 2026 beschäftigt?', 'Jury', 2),
('Fluktuation je Wirtschaftszweig 2025', 'Jury', 3),
('Was ist aus ÖNACE-Abschnitt J geworden?', 'Klassifikation', 4),
('Welche Annahmen gelten für Lieferung 2025-10?', 'Qualitätssicherung', 5),
('Beamte nach Bundesland, Entwicklung', 'Reporting', 6),
('Erkläre Gemeinde 62388', 'Klassifikation', 7),
('Zeig mir den Qualitätsbericht 2025-03', 'Qualitätssicherung', 8),
('Beschäftigte in Tirol nach Monat', 'Reporting', 9),
('Altersverteilung im Juli 2026', 'Reporting', 10)
ON CONFLICT DO NOTHING;
