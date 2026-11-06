-- Phase 2 – classifications. The klass_ tables, transitions and source mappings are filled by
-- `python -m statagent klassifikation` (statagent/etl/classification.py) from the package files.

-- Share of the old code's correspondences that lead to the new code (derived ÖNACE section transitions);
-- NULL = not weighted (official Umsteiger, region changes). German column name: Anhang-B table.
ALTER TABLE klass_uebergang ADD COLUMN IF NOT EXISTS anteil numeric;

-- klass_region is historised as states: version 'Stand JJJJ-01-01' = first snapshot showing the state.
-- For databases seeded before this file (050 now seeds the same value).
UPDATE statistik_dimension SET version = 'Stand 2011-01-01'
WHERE statistik = 'beschaeftigte' AND dimension = 'region' AND version = '-';

-- All classifications in one view (metadata questions, code checks).
CREATE OR REPLACE VIEW klass_alle AS
            SELECT 'klass_region'::text AS klassifikation, * FROM klass_region
  UNION ALL SELECT 'klass_oenace', * FROM klass_oenace
  UNION ALL SELECT 'klass_geschlecht', * FROM klass_geschlecht
  UNION ALL SELECT 'klass_qualifikation', * FROM klass_qualifikation
  UNION ALL SELECT 'klass_alter', * FROM klass_alter;

-- Effective source mappings: straight from the classification files (no rule) or backed by an approved rule.
CREATE OR REPLACE VIEW quellzuordnung_wirksam AS
SELECT q.*
FROM quellzuordnung q
LEFT JOIN ops.rule r ON r.rule_id = q.regel_id
WHERE q.regel_id IS NULL OR r.status = 'approved';

-- Proposed mapping rules (status 'proposed'): the builder writes their quellzuordnung rows from the
-- parameters, but they only take effect (quellzuordnung_wirksam) after approval by a named person.
INSERT INTO ops.rule (rule_id, problem_id, type, title, description, assumption, justification, action, parameters, created_by) VALUES
('R-DQ07', 'DQ-07', 'mapping',
 'Veraltete ÖNACE-2003-Codes DA–DM dem Abschnitt C zuordnen',
 'Steht im Feld OENACE ein Unterabschnitt der ÖNACE 2003 (DA, DB, DC, DD, DF, DG, DH, DI, DJ, DK, DL, DM), wird der Satz dem Abschnitt C „Herstellung von Waren“ der im Berichtsmonat gültigen ÖNACE (bis 12/2024 ÖNACE 2008, ab 01/2025 ÖNACE 2025) zugeordnet. Der gelieferte Code bleibt unverändert gespeichert.',
 'Die Codes stammen aus nicht umgeschlüsselten Altmeldungen nach ÖNACE 2003. Gemeint ist der Abschnitt D „Sachgütererzeugung“ der ÖNACE 2003, der in ÖNACE 2008 und 2025 als Abschnitt C fortgeführt wird – nicht der ÖNACE-2008-Abschnitt D „Energieversorgung“.',
 'Umsteiger ÖNACE 2003 → 2008: 500 von 520 Unterklassen-Korrespondenzen dieser Unterabschnitte führen auf Abschnitt C (96 %); Umsteiger 2008 → 2025: 325 von 327 Korrespondenzen von C führen auf C. Der Beispielbericht 08/2024 bestätigt die Zuordnung: Abschnitt C = 62.204 = 62.154 Verhältnisse mit Code C + 50 mit DA–DM. Betroffen sind 40–51 Sätze je Lieferung (langlaufende Verhältnisse). DE und DN (teilweise J bzw. E/S) kommen in den Lieferungen nicht vor und sind bewusst nicht enthalten; neue Codes meldet die Zuordnungsprüfung.',
 'source_mapping',
 '{"mappings": [{"field": "OENACE", "source_values": ["DA", "DB", "DC", "DD", "DF", "DG", "DH", "DI", "DJ", "DK", "DL", "DM"], "code": "C"}]}',
 'StatAgent-Entwicklung (Vorschlag)'),
('R-DQ08', 'DQ-08', 'mapping',
 'Leere Merkmale der Ausprägung „unbekannt“ zuordnen',
 'Ist BUNDESLAND leer, gilt Bundesland 0 „Bundesland unbekannt“; ist OENACE leer, gilt UNB „Wirtschaftszweig unbekannt“ der im Berichtsmonat gültigen ÖNACE. Vorsorglich gilt dasselbe für leere GESCHLECHT und QUAL (Code UNB, bisher nicht vorgekommen). Die Sätze zählen in allen anderen Gliederungen normal.',
 'Eine fehlende Angabe ist unbekannt, nicht falsch: Das Verhältnis besteht und wird gezählt.',
 'Fachbeschreibung §4 Regel 8 und Anhang A Regel 1: Kein Verhältnis geht verloren. Die Klassifikationsdateien enthalten 0 „Bundesland unbekannt“ und UNB „Wirtschaftszweig unbekannt“; der Beispielbericht 08/2024 weist 1.996 Verhältnisse mit Bundesland unbekannt aus (392.236 − 390.240 in Wirtschaftszweigen eingereiht). BUNDESLAND und OENACE sind immer gemeinsam leer (1.742–2.192 Sätze je Lieferung), meist bei denselben Verhältnissen über alle Lieferungen, daher lässt sich aus früheren Lieferungen nichts ergänzen.',
 'source_mapping',
 '{"mappings": [{"field": "BUNDESLAND", "source_values": [""], "code": "0"}, {"field": "OENACE", "source_values": [""], "code": "UNB"}, {"field": "GESCHLECHT", "source_values": [""], "code": "UNB"}, {"field": "QUAL", "source_values": [""], "code": "UNB"}]}',
 'StatAgent-Entwicklung (Vorschlag)')
ON CONFLICT DO NOTHING;
