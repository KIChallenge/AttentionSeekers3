-- One-off, idempotent migration for databases created before the English clean-up (2026-11-05):
-- renames our own schemas, tables, columns, constraints and enum values in place. Data, approvals and the
-- change log are kept (lossless recoding of enum values; texts, names and times stay unchanged).
-- The Anhang-B model (public) and the delivered tables (roh.lieferung, klassifikation.*) are not touched.
-- On a fresh database nothing here applies; the following files create everything in its final form.

CREATE OR REPLACE FUNCTION pg_temp.rename_constraint(tbl regclass, old_name text, new_name text) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = tbl AND conname = old_name) THEN
    EXECUTE format('ALTER TABLE %s RENAME CONSTRAINT %I TO %I', tbl, old_name, new_name);
  END IF;
END $$;

DO $$
BEGIN
  -- ---------------------------------------------------------------- operations: betrieb -> ops
  IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'betrieb') THEN
    ALTER SCHEMA betrieb RENAME TO ops;

    ALTER TABLE ops.regel RENAME TO rule;
    ALTER TABLE ops.rule RENAME COLUMN regel_id TO rule_id;
    ALTER TABLE ops.rule RENAME COLUMN typ TO type;
    ALTER TABLE ops.rule RENAME COLUMN bezeichnung TO title;
    ALTER TABLE ops.rule RENAME COLUMN beschreibung TO description;
    ALTER TABLE ops.rule RENAME COLUMN annahme TO assumption;
    ALTER TABLE ops.rule RENAME COLUMN begruendung TO justification;
    ALTER TABLE ops.rule RENAME COLUMN aktion TO action;
    ALTER TABLE ops.rule RENAME COLUMN parameter TO parameters;
    ALTER TABLE ops.rule RENAME COLUMN regelwerk TO rule_set;
    ALTER TABLE ops.rule RENAME COLUMN erstellt_von TO created_by;
    ALTER TABLE ops.rule RENAME COLUMN erstellt_am TO created_at;
    ALTER TABLE ops.rule RENAME COLUMN freigegeben_von TO approved_by;
    ALTER TABLE ops.rule RENAME COLUMN freigegeben_am TO approved_at;
    ALTER TABLE ops.rule DROP CONSTRAINT IF EXISTS regel_typ_check, DROP CONSTRAINT IF EXISTS regel_status_check;
    PERFORM pg_temp.rename_constraint('ops.rule', 'regel_pkey', 'rule_pkey');
    UPDATE ops.rule SET
      type = CASE type WHEN 'einlese' THEN 'reading' WHEN 'pruef' THEN 'check' WHEN 'zaehl' THEN 'counting'
                       WHEN 'zuordnung' THEN 'mapping' ELSE type END,
      status = CASE status WHEN 'vorgeschlagen' THEN 'proposed' WHEN 'freigegeben' THEN 'approved'
                           WHEN 'abgelehnt' THEN 'rejected' WHEN 'ausser_kraft' THEN 'retired' ELSE status END,
      action = CASE action WHEN 'spalten_tauschen' THEN 'swap_columns' WHEN 'duplikate_einmal' THEN 'count_duplicates_once'
                           WHEN 'ueberlappung_kuerzen' THEN 'trim_overlap' WHEN 'luecke_schliessen' THEN 'close_gap'
                           WHEN 'quellzuordnung' THEN 'source_mapping' ELSE action END;
    UPDATE ops.rule SET parameters = jsonb_build_object('deliveries', parameters->'lieferungen') WHERE parameters ? 'lieferungen';
    UPDATE ops.rule SET parameters = jsonb_build_object('mappings', (
        SELECT jsonb_agg(jsonb_build_object('field', m->>'merkmal', 'source_values', m->'quellwerte', 'code', m->>'code'))
        FROM jsonb_array_elements(parameters->'zuordnungen') m))
      WHERE parameters ? 'zuordnungen';
    ALTER TABLE ops.rule ALTER COLUMN status SET DEFAULT 'proposed';
    ALTER TABLE ops.rule
      ADD CONSTRAINT rule_type_check CHECK (type IN ('reading', 'check', 'counting', 'mapping')),
      ADD CONSTRAINT rule_status_check CHECK (status IN ('proposed', 'approved', 'rejected', 'retired'));

    ALTER TABLE ops.freigabe RENAME TO approval;
    ALTER TABLE ops.approval RENAME COLUMN freigabe_id TO approval_id;
    ALTER TABLE ops.approval RENAME COLUMN objekt_typ TO object_type;
    ALTER TABLE ops.approval RENAME COLUMN objekt_id TO object_id;
    ALTER TABLE ops.approval RENAME COLUMN entscheidung TO decision;
    ALTER TABLE ops.approval RENAME COLUMN zeitpunkt TO decided_at;
    ALTER TABLE ops.approval RENAME COLUMN kommentar TO comment;
    ALTER TABLE ops.approval DROP CONSTRAINT IF EXISTS freigabe_objekt_typ_check, DROP CONSTRAINT IF EXISTS freigabe_entscheidung_check;
    PERFORM pg_temp.rename_constraint('ops.approval', 'freigabe_pkey', 'approval_pkey');
    PERFORM pg_temp.rename_constraint('ops.approval', 'freigabe_person_check', 'approval_person_check');
    ALTER SEQUENCE IF EXISTS ops.freigabe_freigabe_id_seq RENAME TO approval_approval_id_seq;
    UPDATE ops.approval SET
      object_type = CASE object_type WHEN 'regel' THEN 'rule' WHEN 'lieferung' THEN 'delivery' ELSE object_type END,
      decision = CASE decision WHEN 'freigegeben' THEN 'approved' WHEN 'abgelehnt' THEN 'rejected' ELSE decision END;
    ALTER TABLE ops.approval
      ADD CONSTRAINT approval_object_type_check CHECK (object_type IN ('rule', 'code', 'delivery')),
      ADD CONSTRAINT approval_decision_check CHECK (decision IN ('approved', 'rejected'));

    ALTER TABLE ops.protokoll RENAME TO change_log;
    ALTER TABLE ops.change_log RENAME COLUMN protokoll_id TO log_id;
    ALTER TABLE ops.change_log RENAME COLUMN zeitpunkt TO logged_at;
    ALTER TABLE ops.change_log RENAME COLUMN anweisung TO instruction;
    ALTER TABLE ops.change_log RENAME COLUMN aenderung TO change;
    ALTER TABLE ops.change_log RENAME COLUMN objekt TO object;
    ALTER TABLE ops.change_log RENAME COLUMN freigegeben_von TO approved_by;
    PERFORM pg_temp.rename_constraint('ops.change_log', 'protokoll_pkey', 'change_log_pkey');
    ALTER SEQUENCE IF EXISTS ops.protokoll_protokoll_id_seq RENAME TO change_log_log_id_seq;
    UPDATE ops.change_log SET object = 'rule:' || substr(object, 7) WHERE object LIKE 'regel:%';

    ALTER TABLE ops.lauf RENAME TO run;
    ALTER TABLE ops.run RENAME COLUMN lauf_id TO run_id;
    ALTER TABLE ops.run RENAME COLUMN art TO kind;
    ALTER TABLE ops.run RENAME COLUMN lieferung TO delivery;
    ALTER TABLE ops.run RENAME COLUMN regelwerk TO rule_set;
    ALTER TABLE ops.run RENAME COLUMN regeln TO rules;
    ALTER TABLE ops.run RENAME COLUMN gestartet_am TO started_at;
    ALTER TABLE ops.run RENAME COLUMN beendet_am TO finished_at;
    ALTER TABLE ops.run RENAME COLUMN zeilen TO row_count;
    ALTER TABLE ops.run RENAME COLUMN pruefsumme TO checksum;
    ALTER TABLE ops.run RENAME COLUMN anmerkung TO note;
    ALTER TABLE ops.run DROP CONSTRAINT IF EXISTS lauf_art_check, DROP CONSTRAINT IF EXISTS lauf_status_check;
    PERFORM pg_temp.rename_constraint('ops.run', 'lauf_pkey', 'run_pkey');
    ALTER SEQUENCE IF EXISTS ops.lauf_lauf_id_seq RENAME TO run_run_id_seq;
    UPDATE ops.run SET
      kind = CASE kind WHEN 'bestand' THEN 'store' WHEN 'monat' THEN 'month' WHEN 'klassifikation' THEN 'classification' ELSE kind END,
      status = CASE status WHEN 'laeuft' THEN 'running' WHEN 'fertig' THEN 'done' WHEN 'fehler' THEN 'failed' ELSE status END;
    ALTER TABLE ops.run ALTER COLUMN status SET DEFAULT 'running';
    ALTER TABLE ops.run
      ADD CONSTRAINT run_kind_check CHECK (kind IN ('store', 'month', 'classification')),
      ADD CONSTRAINT run_status_check CHECK (status IN ('running', 'done', 'failed'));

    ALTER TABLE ops.auffaelligkeit RENAME TO finding;
    ALTER TABLE ops.finding RENAME COLUMN auffaelligkeit_id TO finding_id;
    ALTER TABLE ops.finding RENAME COLUMN lauf_id TO run_id;
    ALTER TABLE ops.finding RENAME COLUMN lieferung TO delivery;
    ALTER TABLE ops.finding RENAME COLUMN ebene TO level;
    ALTER TABLE ops.finding RENAME COLUMN beschreibung TO description;
    ALTER TABLE ops.finding RENAME COLUMN umfang TO extent;
    ALTER TABLE ops.finding RENAME COLUMN beispiel_ids TO example_ids;
    ALTER TABLE ops.finding RENAME COLUMN beleg_sql TO evidence_sql;
    ALTER TABLE ops.finding RENAME COLUMN einstufung TO classification;
    ALTER TABLE ops.finding RENAME COLUMN massnahme TO measure;
    ALTER TABLE ops.finding RENAME COLUMN regel_id TO rule_id;
    ALTER TABLE ops.finding RENAME COLUMN rueckfrage_id TO inquiry_id;
    ALTER TABLE ops.finding DROP CONSTRAINT IF EXISTS auffaelligkeit_ebene_check, DROP CONSTRAINT IF EXISTS auffaelligkeit_einstufung_check;
    PERFORM pg_temp.rename_constraint('ops.finding', 'auffaelligkeit_pkey', 'finding_pkey');
    PERFORM pg_temp.rename_constraint('ops.finding', 'auffaelligkeit_lauf_id_fkey', 'finding_run_id_fkey');
    PERFORM pg_temp.rename_constraint('ops.finding', 'auffaelligkeit_regel_id_fkey', 'finding_rule_id_fkey');
    ALTER SEQUENCE IF EXISTS ops.auffaelligkeit_auffaelligkeit_id_seq RENAME TO finding_finding_id_seq;
    UPDATE ops.finding SET
      level = CASE level WHEN 'Satz' THEN 'record' WHEN 'Aggregat' THEN 'aggregate' WHEN 'Lieferung' THEN 'delivery' ELSE level END,
      classification = CASE classification WHEN 'erklaert_plausibel' THEN 'explained_plausible'
                                           WHEN 'erklaert_datenproblem' THEN 'explained_data_problem'
                                           WHEN 'nicht_erklaerbar' THEN 'unexplained' ELSE classification END;
    ALTER TABLE ops.finding
      ADD CONSTRAINT finding_level_check CHECK (level IN ('record', 'aggregate', 'delivery')),
      ADD CONSTRAINT finding_classification_check
        CHECK (classification IN ('explained_plausible', 'explained_data_problem', 'unexplained'));

    ALTER TABLE ops.rueckfrage RENAME TO inquiry;
    ALTER TABLE ops.inquiry RENAME COLUMN rueckfrage_id TO inquiry_id;
    ALTER TABLE ops.inquiry RENAME COLUMN lieferung TO delivery;
    ALTER TABLE ops.inquiry RENAME COLUMN frage TO question;
    ALTER TABLE ops.inquiry RENAME COLUMN vorschlag TO proposal;
    ALTER TABLE ops.inquiry RENAME COLUMN umfang TO extent;
    ALTER TABLE ops.inquiry RENAME COLUMN beispiel_ids TO example_ids;
    ALTER TABLE ops.inquiry RENAME COLUMN beleg_sql TO evidence_sql;
    ALTER TABLE ops.inquiry RENAME COLUMN gestellt_am TO asked_on;
    ALTER TABLE ops.inquiry RENAME COLUMN antwort TO answer;
    ALTER TABLE ops.inquiry RENAME COLUMN beantwortet_am TO answered_on;
    ALTER TABLE ops.inquiry RENAME COLUMN umgesetzt_als_regel TO implemented_as_rule;
    PERFORM pg_temp.rename_constraint('ops.inquiry', 'rueckfrage_pkey', 'inquiry_pkey');
    PERFORM pg_temp.rename_constraint('ops.inquiry', 'rueckfrage_umgesetzt_als_regel_fkey', 'inquiry_implemented_as_rule_fkey');
  END IF;

  -- ---------------------------------------------------------------- versioned store: bestand -> store
  IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'bestand') THEN
    ALTER SCHEMA bestand RENAME TO store;
    ALTER FUNCTION store.iso_datum(text) RENAME TO iso_date;

    ALTER TABLE store.abschnitt RENAME TO segment;
    ALTER TABLE store.segment RENAME COLUMN lieferung TO delivery;
    ALTER TABLE store.segment RENAME COLUMN geburtsdatum_roh TO birth_date_raw;
    ALTER TABLE store.segment RENAME COLUMN geschlecht TO sex;
    ALTER TABLE store.segment RENAME COLUMN beginn_roh TO begin_raw;
    ALTER TABLE store.segment RENAME COLUMN ende_roh TO end_raw;
    ALTER TABLE store.segment RENAME COLUMN kopie_nr TO copy_no;
    ALTER TABLE store.segment RENAME COLUMN geburtsdatum TO birth_date;
    ALTER TABLE store.segment RENAME COLUMN geburtsjahr TO birth_year;
    ALTER TABLE store.segment RENAME COLUMN beginn TO begin_date;
    ALTER TABLE store.segment RENAME COLUMN ende TO end_date;
    ALTER TABLE store.segment RENAME COLUMN ende_wirksam TO effective_end;
    ALTER TABLE store.segment RENAME COLUMN zaehlt TO counted;
    ALTER TABLE store.segment RENAME COLUMN probleme TO problems;
    ALTER TABLE store.segment RENAME COLUMN regeln TO rules;
    ALTER TABLE store.segment RENAME COLUMN lauf_id TO run_id;
    ALTER INDEX IF EXISTS store.abschnitt_lieferung_vvh RENAME TO segment_delivery_vvh;
    ALTER INDEX IF EXISTS store.abschnitt_lieferung_person RENAME TO segment_delivery_person;

    ALTER TABLE store.profil RENAME TO profile;
    ALTER TABLE store.profile RENAME COLUMN lieferung TO delivery;
    ALTER TABLE store.profile RENAME COLUMN kennzahl TO metric;
    ALTER TABLE store.profile RENAME COLUMN wert TO value;
    ALTER TABLE store.profile RENAME COLUMN lauf_id TO run_id;
    PERFORM pg_temp.rename_constraint('store.profile', 'profil_pkey', 'profile_pkey');
    UPDATE store.profile SET metric = CASE metric
      WHEN 'zeilen' THEN 'row_count' WHEN 'aktiv' THEN 'active' WHEN 'aktiv_geliefert' THEN 'active_as_delivered'
      WHEN 'dq01_saetze' THEN 'dq01_rows' WHEN 'dq03_kopien' THEN 'dq03_copies' WHEN 'dq05_saetze' THEN 'dq05_rows'
      WHEN 'dq06_saetze' THEN 'dq06_rows' WHEN 'dq07_saetze' THEN 'dq07_rows' WHEN 'dq08_saetze' THEN 'dq08_rows'
      WHEN 'dq17_saetze' THEN 'dq17_rows' WHEN 'fd_saetze' THEN 'fd_rows' WHEN 'saetze_mit_regel' THEN 'rows_with_rule'
      ELSE metric END;
  END IF;

  -- ---------------------------------------------------------------- our raw helper tables in the delivered schema roh
  IF to_regclass('roh.datei') IS NOT NULL THEN
    ALTER TABLE roh.datei RENAME TO file;
    ALTER TABLE roh.file RENAME COLUMN pfad TO path;
    ALTER TABLE roh.file RENAME COLUMN bereich TO area;
    ALTER TABLE roh.file RENAME COLUMN groesse TO size_bytes;
    ALTER TABLE roh.file RENAME COLUMN einheiten TO units;
    ALTER TABLE roh.file RENAME COLUMN geladen_am TO loaded_at;
    PERFORM pg_temp.rename_constraint('roh.file', 'datei_pkey', 'file_pkey');
    UPDATE roh.file SET area = 'reference' WHERE area = 'referenz';
    UPDATE roh.file SET format = 'other' WHERE format = 'sonstige';

    ALTER TABLE roh.textzeile RENAME TO text_line;
    ALTER TABLE roh.text_line RENAME COLUMN pfad TO path;
    ALTER TABLE roh.text_line RENAME COLUMN zeile TO line_no;
    ALTER TABLE roh.text_line RENAME COLUMN felder TO fields;
    PERFORM pg_temp.rename_constraint('roh.text_line', 'textzeile_pkey', 'text_line_pkey');
    PERFORM pg_temp.rename_constraint('roh.text_line', 'textzeile_pfad_fkey', 'text_line_path_fkey');

    ALTER TABLE roh.zelle RENAME TO cell;
    ALTER TABLE roh.cell RENAME COLUMN pfad TO path;
    ALTER TABLE roh.cell RENAME COLUMN blatt TO sheet;
    ALTER TABLE roh.cell RENAME COLUMN blatt_nr TO sheet_no;
    ALTER TABLE roh.cell RENAME COLUMN zeile TO row_no;
    ALTER TABLE roh.cell RENAME COLUMN spalte TO col_no;
    ALTER TABLE roh.cell RENAME COLUMN zelle TO cell_ref;
    ALTER TABLE roh.cell RENAME COLUMN typ TO type;
    ALTER TABLE roh.cell RENAME COLUMN wert TO value;
    PERFORM pg_temp.rename_constraint('roh.cell', 'zelle_pkey', 'cell_pkey');
    PERFORM pg_temp.rename_constraint('roh.cell', 'zelle_pfad_fkey', 'cell_path_fkey');

    ALTER TABLE roh.zellbereich_verbunden RENAME TO merged_range;
    ALTER TABLE roh.merged_range RENAME COLUMN pfad TO path;
    ALTER TABLE roh.merged_range RENAME COLUMN blatt TO sheet;
    ALTER TABLE roh.merged_range RENAME COLUMN bereich TO cell_range;
    PERFORM pg_temp.rename_constraint('roh.merged_range', 'zellbereich_verbunden_pkey', 'merged_range_pkey');
    PERFORM pg_temp.rename_constraint('roh.merged_range', 'zellbereich_verbunden_pfad_fkey', 'merged_range_path_fkey');

    ALTER TABLE roh.pdf_seite RENAME TO pdf_page;
    ALTER TABLE roh.pdf_page RENAME COLUMN pfad TO path;
    ALTER TABLE roh.pdf_page RENAME COLUMN seite TO page_no;
    PERFORM pg_temp.rename_constraint('roh.pdf_page', 'pdf_seite_pkey', 'pdf_page_pkey');
    PERFORM pg_temp.rename_constraint('roh.pdf_page', 'pdf_seite_pfad_fkey', 'pdf_page_path_fkey');
  END IF;
END $$;

DROP FUNCTION IF EXISTS pg_temp.rename_constraint(regclass, text, text);
