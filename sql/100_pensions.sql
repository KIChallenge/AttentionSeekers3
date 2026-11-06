-- Phase 7 – pension statistic from the aggregated carrier reports (pensionen/, Tabelle 12 and 13, 2018–2025).
-- Classifications, transitions and source mappings are data (T3); statagent/etl/pensions.py parses the files by header text.

DO $$
DECLARE begriff text;
BEGIN
  FOREACH begriff IN ARRAY ARRAY['versicherungstraeger', 'pensionsart'] LOOP
    EXECUTE format($t$
      CREATE TABLE IF NOT EXISTS %I (
        version text NOT NULL DEFAULT '-', code text NOT NULL, bezeichnung text NOT NULL, ebene text NOT NULL,
        uebergeordnet text, gueltig_von date, gueltig_bis date, attribute jsonb NOT NULL DEFAULT '{}',
        PRIMARY KEY (version, code))$t$, 'klass_' || begriff);
  END LOOP;
END $$;

-- Carriers and insurance areas (Versicherungsbereiche = former independent carriers, NOT the Qualifikation, PEN-05).
INSERT INTO klass_versicherungstraeger (version, code, bezeichnung, ebene, uebergeordnet, gueltig_von, gueltig_bis, attribute) VALUES
('-', 'PV',       'Pensionsversicherung insgesamt',                                   'Gesamt',  NULL,      NULL, NULL, '{"berechnet": true}'),
('-', 'PV-UNS',   'Pensionsversicherung der Unselbständigen',                          'Gruppe',  'PV',      NULL, NULL, '{"berechnet": true}'),
('-', 'PV-SELB',  'Pensionsversicherung der Selbständigen',                            'Gruppe',  'PV',      NULL, NULL, '{"berechnet": true}'),
('-', 'PVA',      'Pensionsversicherungsanstalt',                                      'Träger',  'PV-UNS',  '2003-01-01', NULL, '{}'),
('-', 'PVA-ARB',  'PVA – Bereich Arbeiter (frühere PVA der Arbeiter)',                 'Versicherungsbereich', 'PVA', '2003-01-01', NULL, '{"hinweis": "Versicherungsbereich, nicht die Qualifikation Arbeiter der Beschäftigtenstatistik"}'),
('-', 'PVA-ANG',  'PVA – Bereich Angestellte (frühere PVA der Angestellten)',          'Versicherungsbereich', 'PVA', '2003-01-01', NULL, '{"hinweis": "Versicherungsbereich, nicht die Qualifikation Angestellte der Beschäftigtenstatistik"}'),
('-', 'VAEB',     'Versicherungsanstalt für Eisenbahnen und Bergbau',                  'Träger',  'PV-UNS',  NULL, '2019-12-31', '{}'),
('-', 'VAEB-EB',  'VAEB – Bereich Eisenbahnen',                                        'Versicherungsbereich', 'VAEB', NULL, '2019-12-31', '{}'),
('-', 'VAEB-BB',  'VAEB – Bereich Bergbau',                                            'Versicherungsbereich', 'VAEB', NULL, '2019-12-31', '{}'),
('-', 'BVAEB',    'Versicherungsanstalt öffentlich Bediensteter, Eisenbahnen und Bergbau', 'Träger', 'PV-UNS', '2020-01-01', NULL, '{}'),
('-', 'BVAEB-EB', 'BVAEB – Bereich Eisenbahn',                                         'Versicherungsbereich', 'BVAEB', '2020-01-01', NULL, '{}'),
('-', 'BVAEB-BB', 'BVAEB – Bereich Bergbau',                                           'Versicherungsbereich', 'BVAEB', '2020-01-01', NULL, '{}'),
('-', 'SVA',      'Sozialversicherungsanstalt der gewerblichen Wirtschaft',            'Träger',  'PV-SELB', NULL, '2019-12-31', '{}'),
('-', 'SVB',      'Sozialversicherungsanstalt der Bauern',                             'Träger',  'PV-SELB', NULL, '2019-12-31', '{}'),
('-', 'VAN',      'Versicherungsanstalt des österreichischen Notariates',              'Träger',  'PV-SELB', NULL, '2019-12-31', '{"hinweis": "meldet nur den Pensionsstand (Tabelle 12), PEN-04"}'),
('-', 'SVS',      'Sozialversicherungsanstalt der Selbständigen',                      'Träger',  'PV-SELB', '2020-01-01', NULL, '{}'),
('-', 'SVS-GW',   'SVS – Bereich gewerbliche Wirtschaft (frühere SVA)',                'Versicherungsbereich', 'SVS', '2020-01-01', NULL, '{"hinweis": "enthält ab 2020 auch die Pensionen des Notariates (kein eigener Bereich, PEN-06)"}'),
('-', 'SVS-LW',   'SVS – Bereich Landwirtschaft (frühere SVB)',                        'Versicherungsbereich', 'SVS', '2020-01-01', NULL, '{}')
ON CONFLICT DO NOTHING;

INSERT INTO klass_pensionsart (version, code, bezeichnung, ebene, uebergeordnet, attribute) VALUES
('-', 'GES',   'Pensionen insgesamt',                                     'Pensionsart', NULL,  '{"tabelle": 12, "berechnet": true}'),
('-', 'GEM',   'Pensionen wegen geminderter Arbeitsfähigkeit/Erwerbsunfähigkeit', 'Pensionsart', 'GES', '{"tabelle": 12}'),
('-', 'ALTER', 'Alterspensionen',                                         'Pensionsart', 'GES', '{"tabelle": 12}'),
('-', 'WIT',   'Witwen-/Witwerpensionen',                                 'Pensionsart', 'GES', '{"tabelle": 12}'),
('-', 'WAI',   'Waisenpensionen',                                         'Pensionsart', 'GES', '{"tabelle": 12}'),
('-', 'VAP',   'Vorzeitige Alterspensionen insgesamt',                    'Art der vorzeitigen Alterspension', NULL, '{"tabelle": 13, "berechnet": true, "hinweis": "Teilmenge der Alterspensionen"}'),
('-', 'LVD',   'bei langer Versicherungsdauer',                           'Art der vorzeitigen Alterspension', 'VAP', '{"tabelle": 13}'),
('-', 'KOR',   'Korridorpension',                                         'Art der vorzeitigen Alterspension', 'VAP', '{"tabelle": 13}'),
('-', 'LZV',   'Langzeitversicherte',                                     'Art der vorzeitigen Alterspension', 'VAP', '{"tabelle": 13}'),
('-', 'SA1',   'Schwerarbeitspension § 607 Abs. 14 ASVG',                 'Art der vorzeitigen Alterspension', 'VAP', '{"tabelle": 13}'),
('-', 'SA2',   'Schwerarbeitspension § 4 Abs. 3 APG',                     'Art der vorzeitigen Alterspension', 'VAP', '{"tabelle": 13}')
ON CONFLICT DO NOTHING;

-- Carrier mergers on 1.1.2020 (PEN-06): n:1 transitions with validity date.
INSERT INTO klass_uebergang (klassifikation, version_alt, code_alt, version_neu, code_neu, beziehung, gueltig_ab, quelle, anmerkung) VALUES
('klass_versicherungstraeger', '-', 'SVA',     '-', 'SVS',      'n:1', '2020-01-01', 'pensionen/LIESMICH.txt', 'SVA und SVB zur SVS zusammengelegt'),
('klass_versicherungstraeger', '-', 'SVB',     '-', 'SVS',      'n:1', '2020-01-01', 'pensionen/LIESMICH.txt', 'SVA und SVB zur SVS zusammengelegt'),
('klass_versicherungstraeger', '-', 'VAN',     '-', 'SVS',      'n:1', '2020-01-01', 'pensionen/LIESMICH.txt', 'Pensionsversicherung des Notariates ging in die SVS über; kein eigener Bereich'),
('klass_versicherungstraeger', '-', 'SVA',     '-', 'SVS-GW',   '1:1', '2020-01-01', 'pensionen/LIESMICH.txt', 'als Bereich gewerbliche Wirtschaft weitergeführt'),
('klass_versicherungstraeger', '-', 'SVB',     '-', 'SVS-LW',   '1:1', '2020-01-01', 'pensionen/LIESMICH.txt', 'als Bereich Landwirtschaft weitergeführt'),
('klass_versicherungstraeger', '-', 'VAEB',    '-', 'BVAEB',    'n:1', '2020-01-01', 'pensionen/LIESMICH.txt', 'VAEB und BVA zur BVAEB zusammengelegt (BVA meldet hier keine Pensionen)'),
('klass_versicherungstraeger', '-', 'VAEB-EB', '-', 'BVAEB-EB', '1:1', '2020-01-01', 'pensionen/LIESMICH.txt', 'Bereich Eisenbahn weitergeführt'),
('klass_versicherungstraeger', '-', 'VAEB-BB', '-', 'BVAEB-BB', '1:1', '2020-01-01', 'pensionen/LIESMICH.txt', 'Bereich Bergbau weitergeführt')
ON CONFLICT DO NOTHING;

-- Source mappings: how each carrier writes area, pension type and sex (PEN-08: seven spellings of sex).
INSERT INTO quellzuordnung (quelle, merkmal, quellwert, klassifikation, version, code, gueltig_von, regel_id) VALUES
('PV-Meldung', 'Geschlecht', 'Männer', 'klass_geschlecht', '-', 'M', '0001-01-01', NULL),
('PV-Meldung', 'Geschlecht', 'Frauen', 'klass_geschlecht', '-', 'W', '0001-01-01', NULL),
('PV-Meldung', 'Geschlecht', 'Witwer', 'klass_geschlecht', '-', 'M', '0001-01-01', NULL),
('PV-Meldung', 'Geschlecht', 'Witwen', 'klass_geschlecht', '-', 'W', '0001-01-01', NULL),
('PV-Meldung', 'Geschlecht', 'M', 'klass_geschlecht', '-', 'M', '0001-01-01', NULL),
('PV-Meldung', 'Geschlecht', 'F', 'klass_geschlecht', '-', 'W', '0001-01-01', NULL),
('PV-Meldung', 'Geschlecht', 'W', 'klass_geschlecht', '-', 'W', '0001-01-01', NULL),
('PV-Meldung', 'Geschlecht', 'm', 'klass_geschlecht', '-', 'M', '0001-01-01', NULL),
('PV-Meldung', 'Geschlecht', 'w', 'klass_geschlecht', '-', 'W', '0001-01-01', NULL),
('PV-Meldung', 'Geschlecht', 'männlich', 'klass_geschlecht', '-', 'M', '0001-01-01', NULL),
('PV-Meldung', 'Geschlecht', 'weiblich', 'klass_geschlecht', '-', 'W', '0001-01-01', NULL),
('PV-Meldung', 'Pensionsart', 'geminderte Arbeitsfähigkeit/Erwerbsunfähigkeit', 'klass_pensionsart', '-', 'GEM', '0001-01-01', NULL),
('PV-Meldung', 'Pensionsart', 'Alter', 'klass_pensionsart', '-', 'ALTER', '0001-01-01', NULL),
('PV-Meldung', 'Pensionsart', 'Witwen/Witwer', 'klass_pensionsart', '-', 'WIT', '0001-01-01', NULL),
('PV-Meldung', 'Pensionsart', 'Waisen', 'klass_pensionsart', '-', 'WAI', '0001-01-01', NULL),
('PV-Meldung', 'Pensionsart', 'GEM', 'klass_pensionsart', '-', 'GEM', '0001-01-01', NULL),
('PV-Meldung', 'Pensionsart', 'ALT', 'klass_pensionsart', '-', 'ALTER', '0001-01-01', NULL),
('PV-Meldung', 'Pensionsart', 'WIT', 'klass_pensionsart', '-', 'WIT', '0001-01-01', NULL),
('PV-Meldung', 'Pensionsart', 'WAI', 'klass_pensionsart', '-', 'WAI', '0001-01-01', NULL),
('PV-Meldung', 'Pensionsart', 'lange Versicherungsdauer', 'klass_pensionsart', '-', 'LVD', '0001-01-01', NULL),
('PV-Meldung', 'Pensionsart', 'Korridorpension', 'klass_pensionsart', '-', 'KOR', '0001-01-01', NULL),
('PV-Meldung', 'Pensionsart', 'Langzeitversicherte', 'klass_pensionsart', '-', 'LZV', '0001-01-01', NULL),
('PV-Meldung', 'Pensionsart', 'Schwerarbeit § 607/14 ASVG', 'klass_pensionsart', '-', 'SA1', '0001-01-01', NULL),
('PV-Meldung', 'Pensionsart', 'Schwerarbeit § 4 Abs. 3 APG', 'klass_pensionsart', '-', 'SA2', '0001-01-01', NULL),
('PV-Meldung', 'Pensionsart', 'LVD', 'klass_pensionsart', '-', 'LVD', '0001-01-01', NULL),
('PV-Meldung', 'Pensionsart', 'KOR', 'klass_pensionsart', '-', 'KOR', '0001-01-01', NULL),
('PV-Meldung', 'Pensionsart', 'LZV', 'klass_pensionsart', '-', 'LZV', '0001-01-01', NULL),
('PV-Meldung', 'Pensionsart', 'SA1', 'klass_pensionsart', '-', 'SA1', '0001-01-01', NULL),
('PV-Meldung', 'Pensionsart', 'SA2', 'klass_pensionsart', '-', 'SA2', '0001-01-01', NULL),
('PV-Meldung', 'Bereich', 'davon Arbeiter', 'klass_versicherungstraeger', '-', 'PVA-ARB', '0001-01-01', NULL),
('PV-Meldung', 'Bereich', 'davon Angestellte', 'klass_versicherungstraeger', '-', 'PVA-ANG', '0001-01-01', NULL),
('PV-Meldung', 'Bereich', 'Pensionsversicherungsanstalt gesamt', 'klass_versicherungstraeger', '-', 'PVA', '0001-01-01', NULL),
('PV-Meldung', 'Bereich', 'Eisenbahn', 'klass_versicherungstraeger', '-', 'VAEB-EB', '0001-01-01', NULL),
('PV-Meldung', 'Bereich', 'Bergbau', 'klass_versicherungstraeger', '-', 'VAEB-BB', '0001-01-01', NULL),
('PV-Meldung', 'Bereich', 'Eisenbahn', 'klass_versicherungstraeger', '-', 'BVAEB-EB', '2020-01-01', NULL),
('PV-Meldung', 'Bereich', 'Bergbau', 'klass_versicherungstraeger', '-', 'BVAEB-BB', '2020-01-01', NULL),
('PV-Meldung', 'Bereich', 'GW', 'klass_versicherungstraeger', '-', 'SVS-GW', '0001-01-01', NULL),
('PV-Meldung', 'Bereich', 'LW', 'klass_versicherungstraeger', '-', 'SVS-LW', '0001-01-01', NULL),
('PV-Meldung', 'Bereich', 'Gewerbliche Wirtschaft', 'klass_versicherungstraeger', '-', 'SVS-GW', '0001-01-01', NULL),
('PV-Meldung', 'Bereich', 'Landwirtschaft', 'klass_versicherungstraeger', '-', 'SVS-LW', '0001-01-01', NULL),
('PV-Meldung', 'Bereich', 'SVA', 'klass_versicherungstraeger', '-', 'SVA', '0001-01-01', NULL),
('PV-Meldung', 'Bereich', 'SVB', 'klass_versicherungstraeger', '-', 'SVB', '0001-01-01', NULL),
('PV-Meldung', 'Bereich', 'VAN', 'klass_versicherungstraeger', '-', 'VAN', '0001-01-01', NULL)
ON CONFLICT DO NOTHING;
-- the VAEB area rows also match from 2020 on (BVAEB): end their validity
UPDATE quellzuordnung SET gueltig_bis = '2019-12-31'
WHERE quelle = 'PV-Meldung' AND merkmal = 'Bereich' AND code IN ('VAEB-EB', 'VAEB-BB') AND gueltig_bis IS NULL;

-- Description, dimensions and variables of the new statistic (Anhang B: own stat_ table, shared variable table and klass_ tables).
INSERT INTO statistik_beschreibung (statistik, name, quelle, statistiktyp, beschreibung, anmerkungen, fussnoten) VALUES
('pensionen', 'Pensionsstatistik (Tabellen 12 und 13 der Jahresergebnisse)',
 'Meldungen der Pensionsversicherungsträger 2018–2025 (pensionen/, je Träger und Jahr eine Excel-Datei in eigenem Format)',
 'aggregiert',
 'Stand der Pensionen nach Pensionsart und Geschlecht (Tabelle 12) und vorzeitige Alterspensionen nach Art und Geschlecht (Tabelle 13), Jahresdurchschnitt, je Versicherungsträger und Versicherungsbereich; Summen über alle Träger (PV insgesamt, PV der Unselbständigen, PV der Selbständigen) berechnet.',
 'Versicherungsbereiche (z. B. PVA Arbeiter/Angestellte) sind frühere Träger, nicht die Qualifikation der Beschäftigtenstatistik.',
 'Zeitreihenbruch 2020: SVA + SVB + VAN → SVS, VAEB → BVAEB; das Notariat ist ab 2020 kein eigener Bereich. VAN meldet keine vorzeitigen Alterspensionen (Status „nicht gemeldet“, nicht 0).')
ON CONFLICT DO NOTHING;
INSERT INTO statistik_dimension (statistik, dimension, klassifikation, ebene, version) VALUES
('pensionen', 'versicherungstraeger', 'klass_versicherungstraeger', 'Versicherungsbereich', '-'),
('pensionen', 'pensionsart', 'klass_pensionsart', 'Pensionsart', '-'),
('pensionen', 'geschlecht', 'klass_geschlecht', 'Geschlecht', '-')
ON CONFLICT DO NOTHING;
INSERT INTO variable (statistik, variablencode, variablenbezeichnung, beschreibung, einheit, berechnungslogik) VALUES
('pensionen', 'Pensionen', 'Pensionen (Pensionsstand)', 'Zahl der Pensionen im Jahresdurchschnitt laut Meldung des Trägers (Tabelle 12).', 'Anzahl',
 'Wert der Meldung je Träger/Bereich, Pensionsart und Geschlecht; Summen über Bereiche, Träger und Pensionsarten berechnet.'),
('pensionen', 'VorzeitigeAlterspensionen', 'Vorzeitige Alterspensionen', 'Zahl der vorzeitigen Alterspensionen im Jahresdurchschnitt (Tabelle 13).', 'Anzahl',
 'Wert der Meldung je Träger/Bereich, Art und Geschlecht; Summen berechnet; VAN: nicht gemeldet.')
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS stat_pensionen (
  zeitraum_art          text NOT NULL CHECK (zeitraum_art IN ('Jahresdurchschnitt')),
  zeitraum_von          date NOT NULL,
  zeitraum_bis          date NOT NULL,
  versicherungstraeger  text NOT NULL,
  pensionsart           text NOT NULL,
  geschlecht            text NOT NULL,
  variable              text NOT NULL,
  wert                  numeric,                 -- NULL with status 'nicht gemeldet' (VAN Tabelle 13, PEN-04)
  status                text NOT NULL CHECK (status IN ('vorlaeufig', 'endgueltig', 'gesperrt', 'nicht gemeldet')),
  stand                 text NOT NULL,           -- e.g. 'Meldung PVA 2025' or 'berechnet aus den Meldungen 2025'
  lauf_id               bigint,
  PRIMARY KEY (zeitraum_von, versicherungstraeger, pensionsart, geschlecht, variable)
);

-- Every parsed cell with its source (file, sheet, cell) – the Quellennachweis of the pension numbers.
CREATE TABLE IF NOT EXISTS store.pension_cell (
  path text NOT NULL, sheet text NOT NULL, cell_ref text NOT NULL, raw_value text NOT NULL, value numeric,
  jahr integer NOT NULL, tabelle integer NOT NULL, bereich_raw text, art_raw text, geschlecht_raw text,
  versicherungstraeger text, pensionsart text, geschlecht text, format text NOT NULL, run_id bigint NOT NULL,
  PRIMARY KEY (path, sheet, cell_ref)
);

ALTER TABLE ops.run DROP CONSTRAINT IF EXISTS run_kind_check;
ALTER TABLE ops.run ADD CONSTRAINT run_kind_check
  CHECK (kind IN ('store', 'month', 'classification', 'export', 'ministry', 'code', 'synth', 'model', 'pension'));

CREATE OR REPLACE VIEW klass_alle AS
            SELECT 'klass_region'::text AS klassifikation, * FROM klass_region
  UNION ALL SELECT 'klass_oenace', * FROM klass_oenace
  UNION ALL SELECT 'klass_geschlecht', * FROM klass_geschlecht
  UNION ALL SELECT 'klass_qualifikation', * FROM klass_qualifikation
  UNION ALL SELECT 'klass_alter', * FROM klass_alter
  UNION ALL SELECT 'klass_versicherungstraeger', * FROM klass_versicherungstraeger
  UNION ALL SELECT 'klass_pensionsart', * FROM klass_pensionsart;
