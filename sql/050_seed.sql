-- Seed data: description and variables of the employment statistic, and the proposed reading rules.
-- ON CONFLICT DO NOTHING: re-running never overwrites approvals or later edits.
-- Rule texts are German (shown to the Fachabteilung and in the UI); column names and enum values are English.

INSERT INTO statistik_beschreibung (statistik, name, quelle, statistiktyp, beschreibung, anmerkungen, fussnoten) VALUES
('beschaeftigte', 'Beschäftigtenstatistik',
 'Zentrale Versicherungsdatei – Monatslieferungen 2024-08 bis 2026-07 (Vollabzug der letzten drei Monate)',
 'Einzeldaten',
 'Beschäftigungsverhältnisse nach Bundesland des Arbeitsortes, Wirtschaftszweig, Geschlecht, Beschäftigungskategorie und Alter. Zählregeln laut Fachbeschreibung §4.',
 'Synthetische Daten im Maßstab von etwa 1:10, keine amtlichen Zahlen.',
 'Wirtschaftszweig bis 12/2024 nach ÖNACE 2008, ab 01/2025 nach ÖNACE 2025 (Klassifikationsbruch).')
ON CONFLICT DO NOTHING;

INSERT INTO statistik_dimension (statistik, dimension, klassifikation, ebene, version, gueltig_von, gueltig_bis) VALUES
('beschaeftigte', 'region',        'klass_region',        'Bundesland',     'Stand 2011-01-01', '0001-01-01', NULL),
('beschaeftigte', 'oenace',        'klass_oenace',        'Abschnitt',      '2008', '0001-01-01', '2024-12-31'),
('beschaeftigte', 'oenace',        'klass_oenace',        'Abschnitt',      '2025', '2025-01-01', NULL),
('beschaeftigte', 'geschlecht',    'klass_geschlecht',    'Geschlecht',     '-',    '0001-01-01', NULL),
('beschaeftigte', 'qualifikation', 'klass_qualifikation', 'Qualifikation',  '-',    '0001-01-01', NULL),
('beschaeftigte', 'alter',         'klass_alter',         'Altersjahr',     '-',    '0001-01-01', NULL)
ON CONFLICT DO NOTHING;

INSERT INTO variable (statistik, variablencode, variablenbezeichnung, beschreibung, einheit, berechnungslogik) VALUES
('beschaeftigte', 'Beschaeftigungsverhaeltnisse', 'Beschäftigungsverhältnisse',
 'Versicherungsverhältnisse (nicht Personen), die am Stichtag – dem Monatsletzten – mit mindestens einem Zeitabschnitt bestehen. Eine Person mit zwei Verhältnissen zählt zweimal.',
 'Anzahl',
 'COUNT(DISTINCT vvh_id) der Abschnitte mit beginn <= Stichtag und (ende leer oder >= Stichtag) aus der Lieferung des Berichtsmonats; Merkmale aus dem Abschnitt am Stichtag; Alter in vollendeten Jahren am Stichtag (Fachbeschreibung §4, Z1–Z7).')
ON CONFLICT DO NOTHING;

-- Proposed reading rules (status 'proposed'): they take effect only after approval by a named person.
INSERT INTO ops.rule (rule_id, problem_id, type, title, description, assumption, justification, action, parameters, created_by) VALUES
('R-DQ01', 'DQ-01', 'reading',
 'Lieferung 2025-06: BEGINN und ENDE vertauscht lesen',
 'Für die Lieferung 2025-06 wird der Wert der Spalte ENDE als Beginn und der Wert der Spalte BEGINN als Ende gelesen. Die gelieferten Werte bleiben unverändert (roh.lieferung, store.segment.begin_raw/end_raw).',
 'Die Lieferung 2025-06 wurde mit vertauschten Spalten BEGINN und ENDE erzeugt.',
 '388.115 Sätze mit leerem BEGINN und gefülltem ENDE, 43.914 mit ENDE < BEGINN, nur 57 unauffällig. Ohne diese Regel wären am 30.06.2025 nur 21 statt rund 394.000 Verhältnisse aktiv. Die Lieferung 2025-07 enthält dieselben Abschnitte in der richtigen Reihenfolge.',
 'swap_columns', '{"deliveries": ["2025-06"]}', 'StatAgent-Entwicklung (Vorschlag)'),
('R-DQ03', 'DQ-03', 'counting',
 'Exakt doppelte Sätze nur einmal berücksichtigen',
 'Identische Sätze innerhalb einer Lieferung werden nur einmal berücksichtigt; die Kopien bleiben gespeichert und markiert (copy_no > 1).',
 'Identische Sätze sind technische Doppellieferungen desselben Zeitabschnitts.',
 'Anhang A Regel 1: Kommt ein Satz in einer Lieferung mehrfach vor, wird das Verhältnis trotzdem nur einmal gezählt. Lieferung 2025-03 enthält 1.663 exakte Duplikate.',
 'count_duplicates_once', '{}', 'StatAgent-Entwicklung (Vorschlag)'),
('R-DQ09', 'DQ-09', 'reading',
 'Überlappende Abschnitte: der spätere gilt ab seinem Beginn',
 'Überlappt ein Abschnitt den nächsten Abschnitt desselben Verhältnisses (oder ist er offen und es folgt ein weiterer, DQ-11), endet er wirksam am Tag vor dem Beginn des nächsten.',
 'Der spätere Abschnitt ist die aktuellere Meldung; das Verhältnis besteht nur einmal.',
 'Fachbeschreibung §2: Ändert sich ein Merkmal, endet der Zeitabschnitt am Vortag und ein neuer beginnt. Ohne Regel wären an überlappenden Tagen zwei Abschnitte mit unterschiedlichen Merkmalen gültig (z. B. VVH 177707).',
 'trim_overlap', '{}', 'StatAgent-Entwicklung (Vorschlag)'),
('R-DQ10', 'DQ-10', 'reading',
 'Lücken zwischen Abschnitten schließen',
 'Beginnt der nächste Abschnitt eines Verhältnisses später als am Tag nach dem Ende des vorigen, gilt der vorige Abschnitt wirksam bis zum Tag vor dem nächsten Beginn.',
 'Das Verhältnis (gleiche VVH_ID) bestand in der Lücke mit den bisherigen Merkmalen weiter.',
 'Fachbeschreibung §2: Die Zeitabschnitte eines Verhältnisses schließen lückenlos aneinander an. Anhang A Regel 1: Kein Verhältnis geht verloren, auch nicht an einem Stichtag innerhalb einer Lücke (z. B. VVH 169362).',
 'close_gap', '{}', 'StatAgent-Entwicklung (Vorschlag)')
ON CONFLICT DO NOTHING;
