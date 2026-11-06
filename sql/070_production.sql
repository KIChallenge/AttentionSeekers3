-- Phase 3 – monthly production runs (`lauf --lieferung JJJJ-MM`), quality reports and the rules they use.
-- Numbers in stat_beschaeftigte come only from statagent/qa/run.py (deterministic SQL, T1).

-- More run kinds: monthly runs, exports (sheets, ministry delivery), generated code, agent answers.
ALTER TABLE ops.run DROP CONSTRAINT IF EXISTS run_kind_check;
ALTER TABLE ops.run ADD CONSTRAINT run_kind_check
  CHECK (kind IN ('store', 'month', 'classification', 'export', 'ministry', 'code', 'synth', 'model', 'pension'));

-- Every record counted in a month (one row per VVH and month): the evidence behind each stat_ value.
-- origin 'delivery' = from the month's own delivery; 'carry_forward' = assumption rule from the previous delivery.
CREATE TABLE IF NOT EXISTS store.month_record (
  rule_set         text NOT NULL,
  month            text NOT NULL,               -- reporting month JJJJ-MM
  vvh_id           text NOT NULL,
  person_id        text,
  origin           text NOT NULL CHECK (origin IN ('delivery', 'carry_forward')),
  source_delivery  text NOT NULL,               -- delivery the attributes come from
  begin_date       date,                        -- segment used for the attributes
  end_date         date,
  sex_raw          text, qual_raw text, oenace_raw text, bundesland_raw text, birth_date_raw text,
  region           text NOT NULL,               -- codes after quellzuordnung_wirksam; 'NZ' = nicht zuordenbar
  oenace           text NOT NULL,
  geschlecht       text NOT NULL,
  qualifikation    text NOT NULL,
  alter            text NOT NULL,
  problems         text[] NOT NULL DEFAULT '{}',
  rules            text[] NOT NULL DEFAULT '{}',
  run_id           bigint NOT NULL
);
ALTER TABLE store.month_record SET UNLOGGED;
CREATE INDEX IF NOT EXISTS month_record_key ON store.month_record (rule_set, month, vvh_id);
CREATE INDEX IF NOT EXISTS month_record_person ON store.month_record (rule_set, month, person_id);

-- Reconciliation and key figures per run (shown in the QB overview and the UI).
CREATE TABLE IF NOT EXISTS ops.run_metric (
  run_id  bigint NOT NULL REFERENCES ops.run,
  metric  text NOT NULL,
  value   numeric NOT NULL,
  PRIMARY KEY (run_id, metric)
);

-- Quality reports (one per month and rule set) and other generated documents, with their file path.
CREATE TABLE IF NOT EXISTS ops.report (
  report_id   bigserial PRIMARY KEY,
  kind        text NOT NULL CHECK (kind IN ('quality_report', 'inquiry', 'sheet', 'ministry', 'calibration')),
  rule_set    text NOT NULL DEFAULT 'basis',
  month       text,
  run_id      bigint REFERENCES ops.run,
  path        text,                              -- relative to the project folder
  content     text,
  sha256      text,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS report_kind_month ON ops.report (kind, rule_set, month);

ALTER TABLE ops.finding ADD COLUMN IF NOT EXISTS rule_set text NOT NULL DEFAULT 'basis';
ALTER TABLE ops.finding ADD COLUMN IF NOT EXISTS check_id text;
ALTER TABLE ops.inquiry ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE ops.approval DROP CONSTRAINT IF EXISTS approval_object_type_check;
ALTER TABLE ops.approval ADD CONSTRAINT approval_object_type_check
  CHECK (object_type IN ('rule', 'code', 'delivery', 'month'));

-- Proposed rules for Phase 3 (status 'proposed': effective only after approval by a named person).
INSERT INTO ops.rule (rule_id, problem_id, type, title, description, assumption, justification, action, parameters, created_by) VALUES
('R-DQ05', 'DQ-05', 'reading',
 'Geburtsmonat 13: Alter aus dem Geburtsjahr',
 'Ist das GEBURTSDATUM ungültig, aber das Jahr lesbar (z. B. 1987-13-05), wird das Alter als Berichtsjahr minus Geburtsjahr gerechnet. Das gelieferte Datum bleibt unverändert gespeichert.',
 'Nur der Monat ist fehlerhaft; Jahr und Tag (immer ≤ 28) sind plausibel. Eine Vertauschung von Tag und Monat ist ausgeschlossen, weil sie Monat 28 ergäbe.',
 'Der Beispielbericht 08/2024 weist nur 7 Verhältnisse mit Alter unbekannt aus (die Fälle über 110 Jahre); die 370 Sätze mit Monat 13 sind dort je Altersjahr mit Berichtsjahr minus Geburtsjahr gezählt (zellgenau nachgerechnet). Ohne die Regel fielen 336–444 Verhältnisse je Monat in „unbekannt“.',
 'age_from_birth_year', '{}', 'StatAgent-Entwicklung (Vorschlag)'),
('R-DQ02', 'DQ-02', 'reading',
 'Lieferung 2025-10 unvollständig: offene Verhältnisse aus 2025-09 fortschreiben',
 'Verhältnisse, die in der Lieferung 2025-09 am 30.09.2025 offen sind (Ende leer) und in der Lieferung 2025-10 vollständig fehlen, werden am Stichtag 31.10.2025 mit den Merkmalen aus 2025-09 gezählt. Ausgenommen sind Verdachtsfälle von Doppelmeldungen (DQ-16). Nur frühere Lieferungen werden verwendet.',
 'Die Lieferung 2025-10 ist technisch unvollständig (rund 20 % der Verhältnisse fehlen zufällig verteilt); ein in einem Vollabzug fehlendes, zuvor offenes Verhältnis besteht weiter.',
 '345.078 statt rund 430.000 Sätze; der Ausfall ist über Bundesland, Qualifikation, Geschlecht und ÖNACE gleich verteilt, auch August und September sind in 2025-10 um 20 % zu niedrig. Anhang A Regel 1: kein Verhältnis geht verloren. Die Lieferung 2025-11 bestätigt die Annahme (Revision im QB 2025-11); Rückfrage an die Fachabteilung empfohlen.',
 'carry_forward', '{"deliveries": ["2025-10"]}', 'StatAgent-Entwicklung (Vorschlag)'),
('R-DQ04', 'DQ-04', 'reading',
 'Lieferung 2025-03 ohne freie Dienstverträge: FD aus 2025-02 fortschreiben',
 'Freie Dienstverträge (ArbeiterFD, AngestellteFD), die in der Lieferung 2025-02 am 28.02.2025 offen sind und in der Lieferung 2025-03 vollständig fehlen, werden am Stichtag 31.03.2025 mit den Merkmalen aus 2025-02 gezählt. Ausgenommen sind Verdachtsfälle von Doppelmeldungen (DQ-16).',
 'Die freien Dienstverträge wurden in der Lieferung 2025-03 technisch nicht mitgeliefert; die Verhältnisse bestehen weiter.',
 'L2025-02: 1.651 FD-Verhältnisse, L2025-03: 0, L2025-04: 1.524. Ein Wegfall aller FD in einem Monat und die Rückkehr im Folgemonat ist keine reale Entwicklung. Anhang A Regel 1: kein Verhältnis geht verloren. Rückfrage an die Fachabteilung empfohlen.',
 'carry_forward', '{"deliveries": ["2025-03"], "qual_suffix": "FD"}', 'StatAgent-Entwicklung (Vorschlag)')
ON CONFLICT DO NOTHING;

-- Revision need (Z4, DQ-12): a published month compared with a later delivery – both values kept, never merged.
CREATE TABLE IF NOT EXISTS ops.revision (
  run_id          bigint NOT NULL REFERENCES ops.run,   -- run of the later delivery
  rule_set        text NOT NULL,
  month           text NOT NULL,                        -- earlier, published reporting month
  delivery        text NOT NULL,                        -- later delivery
  published       bigint NOT NULL,                      -- value from the month's own run
  current         bigint NOT NULL,                      -- value from the later delivery, same counting rules
  new_vvh         bigint NOT NULL,                      -- counted now, not in the published month (late reports)
  vanished_vvh    bigint NOT NULL,                      -- published, not in the later delivery
  vanished_dq16   bigint NOT NULL,                      -- of which suspected double registrations (DQ-16)
  carried_total   bigint NOT NULL DEFAULT 0,            -- published via an assumption rule (carry_forward)
  carried_confirmed bigint NOT NULL DEFAULT 0,          -- of which confirmed by the later delivery
  main_cause      text,
  PRIMARY KEY (run_id, month)
);

-- Speed for the web UI (QB list, evidence): look-ups by run.
CREATE INDEX IF NOT EXISTS finding_run ON ops.finding (run_id);
CREATE INDEX IF NOT EXISTS stat_beschaeftigte_lauf ON stat_beschaeftigte (lauf_id);

-- Flows per month (Zu-/Abgänge against the previous month, same rule set), written by every run – basis for the
-- fluctuation readings in the chat (ops.term 'fluktuation'). Abgänge carry the attributes of the previous month.
CREATE TABLE IF NOT EXISTS store.month_flow (
  rule_set text NOT NULL, month text NOT NULL, kind text NOT NULL CHECK (kind IN ('zu', 'ab')),
  region text NOT NULL, oenace text NOT NULL, geschlecht text NOT NULL, qualifikation text NOT NULL, alter text NOT NULL,
  n bigint NOT NULL, run_id bigint NOT NULL
);
CREATE INDEX IF NOT EXISTS month_flow_key ON store.month_flow (rule_set, month, kind);
