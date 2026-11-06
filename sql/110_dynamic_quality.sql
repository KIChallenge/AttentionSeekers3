-- Dynamic handling of faulty data per statistic (chat / Fragen) and the reworked R-DQ05.
-- Rules as data (T3): the handling options are rows here; statagent/reporting/quality.py implements their actions.

-- Records an approved rule excludes from the count (e.g. R-DQ05 with exclude = true): kept and shown, never lost.
CREATE TABLE IF NOT EXISTS store.month_excluded (LIKE store.month_record INCLUDING DEFAULTS);
ALTER TABLE store.month_excluded ADD COLUMN IF NOT EXISTS reason_rule text;
ALTER TABLE store.month_excluded SET UNLOGGED;
CREATE INDEX IF NOT EXISTS month_excluded_key ON store.month_excluded (rule_set, month, vvh_id);

-- R-DQ05 reworked on instruction of the team (2026-11-05): flag month-13 birth dates as a wrong date format, read day and
-- month swapped where that gives a valid date, optionally exclude. Only changed while still a proposal.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM ops.rule WHERE rule_id = 'R-DQ05' AND status = 'proposed' AND action = 'age_from_birth_year') THEN
    UPDATE ops.rule SET
      title = 'Geburtsdatum mit Monat 13: als falsches Datumsformat markieren, Tag und Monat vertauscht lesen',
      description = 'Ein GEBURTSDATUM der Form JJJJ-13-TT wird als falsches Datumsformat markiert (DQ-05) und mit vertauschtem Tag und Monat gelesen: JJJJ-TT-13, wenn TT ein gültiger Monat (01–12) ist. Ist TT größer als 12, ist kein Tausch möglich; dann gilt der Parameter fallback („unbekannt“ = Alter unbekannt, „jahr“ = Berichtsjahr − Geburtsjahr). Mit dem Parameter exclude = true werden alle Sätze mit Monat 13 nicht gezählt, aber als „nach Regel ausgeschlossen“ im Qualitätsbericht ausgewiesen. Das gelieferte Datum bleibt unverändert gespeichert.',
      assumption = 'Die Geburtsdaten mit Monat 13 sind im Format JJJJ-TT-MM statt JJJJ-MM-TT geliefert worden (Tag und Monat vertauscht); der Tag 13 steht im Monatsfeld.',
      justification = 'Vorgabe des Teams (2026-11-05). Beleg in den Daten: 336–444 Sätze je Lieferung mit Monat 13; die Tage liegen zwischen 01 und 28, ein Tausch ist daher nur bei Tag ≤ 12 möglich (08/2024: 143 von 370 Sätzen), für die übrigen greift der Fallback. Hinweis: Der Beispielbericht 08/2024 rechnet diese Fälle mit Berichtsjahr − Geburtsjahr; mit dem Tausch weichen einzelne Altersjahre in Tabelle 13 ab (siehe Kalibrierung). Ausschließen widerspricht Anhang A Regel 1 und ist deshalb nur als Parameter vorgesehen, sichtbar im Qualitätsbericht.',
      action = 'birth_date_swap',
      parameters = '{"fallback": "unbekannt", "exclude": false}',
      created_by = 'StatAgent-Entwicklung (Vorschlag, überarbeitet nach Vorgabe des Teams)'
    WHERE rule_id = 'R-DQ05';
    INSERT INTO ops.change_log (instruction, change, object, approved_by) VALUES
      ('Geburtsdatum mit Monat 13 als falsches Format markieren, Tag und Monat vertauscht lesen, Ausschluss wählbar',
       'Regelvorschlag R-DQ05 überarbeitet (noch nicht freigegeben): birth_date_swap statt age_from_birth_year', 'rule:R-DQ05', NULL);
  END IF;
END $$;

-- Data problems that can affect a statistic someone asks for, and three handling options each (+ free text in the UI).
CREATE TABLE IF NOT EXISTS ops.dq_option (
  problem_id     text NOT NULL,
  option_id      text NOT NULL,
  label_de       text NOT NULL,
  definition_de  text NOT NULL,
  action         text NOT NULL,                -- implemented in statagent/reporting/quality.py
  is_default     boolean NOT NULL DEFAULT false,
  sort           integer NOT NULL DEFAULT 0,
  PRIMARY KEY (problem_id, option_id)
);
INSERT INTO ops.dq_option (problem_id, option_id, label_de, definition_de, action, is_default, sort) VALUES
('DQ-05', 'tausch', 'Tag und Monat tauschen', 'JJJJ-13-TT als JJJJ-TT-13 lesen, wenn TT ≤ 12; sonst Alter unbekannt.', 'birth_swap', true, 1),
('DQ-05', 'unbekannt', 'Alter „unbekannt“', 'Das Geburtsdatum ist ungültig: Alter unbekannt, in allen anderen Merkmalen gezählt.', 'age_unknown', false, 2),
('DQ-05', 'ausschliessen', 'Sätze ausschließen', 'Verhältnisse mit Monat 13 in dieser Auswertung nicht zählen (Summe sinkt).', 'exclude', false, 3),
('DQ-06', 'unbekannt', 'Alter „unbekannt“', 'Alter über 110 Jahre ist unplausibel: Alter unbekannt (klass_alter).', 'age_unknown', true, 1),
('DQ-06', 'wie_geliefert', 'Alter wie geliefert', 'Rechnerisches Alter aus dem gelieferten Datum verwenden (in „75 u. mehr“).', 'age_raw', false, 2),
('DQ-06', 'ausschliessen', 'Sätze ausschließen', 'Verhältnisse mit Alter über 110 in dieser Auswertung nicht zählen.', 'exclude', false, 3),
('DQ-07', 'abschnitt_c', 'Abschnitt C zuordnen', 'ÖNACE-2003-Codes DA–DM als Abschnitt C (freigegebene Regel R-DQ07).', 'keep', true, 1),
('DQ-07', 'unbekannt', 'Wirtschaftszweig „unbekannt“', 'Veraltete Codes als UNB „Wirtschaftszweig unbekannt“ ausweisen.', 'oenace_unknown', false, 2),
('DQ-07', 'ausschliessen', 'Sätze ausschließen', 'Verhältnisse mit ÖNACE-2003-Code in dieser Auswertung nicht zählen.', 'exclude', false, 3),
('DQ-08', 'unbekannt', 'Eigene Zeile „unbekannt“', 'Leeres Feld als „Bundesland unbekannt“ bzw. „Wirtschaftszweig unbekannt“ (freigegebene Regel R-DQ08).', 'keep', true, 1),
('DQ-08', 'fruehere_lieferung', 'Aus früherer Lieferung ergänzen', 'Wert aus der letzten früheren Lieferung desselben Verhältnisses übernehmen, falls dort gefüllt; sonst unbekannt.', 'fill_from_earlier', false, 2),
('DQ-08', 'ausschliessen', 'Sätze ausschließen', 'Verhältnisse mit leerem Feld in dieser Auswertung nicht zählen.', 'exclude', false, 3),
('DQ-02', 'wie_geliefert', 'Wie geliefert', '10/2025 aus der unvollständigen Lieferung (rund 20 % der Verhältnisse fehlen).', 'keep', true, 1),
('DQ-02', 'fortschreiben', 'Aus 2025-09 fortschreiben', 'In 2025-09 offene, in 2025-10 fehlende Verhältnisse mit den Merkmalen aus 2025-09 zählen (ohne Doppelmeldungsverdacht).', 'carry_forward', false, 2),
('DQ-02', 'ausblenden', 'Monat ausblenden', '10/2025 nicht anzeigen (als Lücke markiert).', 'hide_month', false, 3),
('DQ-04', 'wie_geliefert', 'Wie geliefert', '03/2025 ohne freie Dienstverträge (alle FD fehlen in der Lieferung).', 'keep', true, 1),
('DQ-04', 'fortschreiben', 'FD aus 2025-02 fortschreiben', 'In 2025-02 offene, in 2025-03 fehlende freie Dienstverträge mit den Merkmalen aus 2025-02 zählen.', 'carry_forward', false, 2),
('DQ-04', 'ausblenden', 'Monat ausblenden', '03/2025 nicht anzeigen (als Lücke markiert).', 'hide_month', false, 3),
('DQ-01', 'vertauscht', 'Spalten vertauscht lesen', 'BEGINN und ENDE der Lieferung 2025-06 vertauscht lesen (freigegebene Regel R-DQ01).', 'keep', true, 1),
('DQ-01', 'wie_geliefert', 'Wie geliefert', '06/2025 mit den gelieferten Spalten: fast alle Verhältnisse fallen weg (21 aktiv).', 'as_delivered', false, 2),
('DQ-01', 'ausblenden', 'Monat ausblenden', '06/2025 nicht anzeigen (als Lücke markiert).', 'hide_month', false, 3),
('DQ-16', 'mitzaehlen', 'Mitzählen (wie geliefert)', 'Verdachtsfälle auf Doppelmeldung zählen wie geliefert (wie der Beispielbericht).', 'keep', true, 1),
('DQ-16', 'bestaetigte_ausschliessen', 'Bestätigte ausschließen', 'Verdachtsfälle nicht zählen, die in der nächsten Lieferung fehlen (Wissen aus späterer Lieferung).', 'exclude_confirmed', false, 2),
('DQ-16', 'alle_ausschliessen', 'Alle Verdachtsfälle ausschließen', 'Alle Verdachtsfälle der eigenen Lieferung nicht zählen (auch mögliche echte Zweitjobs).', 'exclude', false, 3)
ON CONFLICT DO NOTHING;

-- Choices made in the chat (incl. free text) – the copy of the affected records lives in work.dq_copy.
CREATE SCHEMA IF NOT EXISTS work;
CREATE TABLE IF NOT EXISTS work.dq_copy (
  copy_id        text NOT NULL,                -- one copy per answer
  problem_id     text NOT NULL,
  option_id      text NOT NULL,
  kind           text NOT NULL CHECK (kind IN ('removed', 'added')),  -- original record taken out / changed record put in
  month          text NOT NULL,
  vvh_id         text NOT NULL,
  region text NOT NULL, oenace text NOT NULL, geschlecht text NOT NULL, qualifikation text NOT NULL, alter text NOT NULL,
  note           text,
  created_at     timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE work.dq_copy SET UNLOGGED;
CREATE INDEX IF NOT EXISTS dq_copy_key ON work.dq_copy (copy_id, kind, month);
CREATE TABLE IF NOT EXISTS ops.dq_choice (
  choice_id    bigserial PRIMARY KEY,
  chosen_at    timestamptz NOT NULL DEFAULT now(),
  "user"       text,
  copy_id      text NOT NULL,
  problem_id   text NOT NULL,
  option_id    text,                           -- NULL = free text only
  free_text    text,
  interpreted  text,                           -- how the free text was understood (option or note)
  rows_removed bigint, rows_added bigint
);

-- More ambiguous terms (PRD §5.3): trigger/resolve patterns and the condition under which to ask are data, too.
ALTER TABLE ops.term ADD COLUMN IF NOT EXISTS trigger_regex text;
ALTER TABLE ops.term ADD COLUMN IF NOT EXISTS resolve_regex text;
ALTER TABLE ops.term ADD COLUMN IF NOT EXISTS ask_when text NOT NULL DEFAULT 'always';
ALTER TABLE ops.term ADD COLUMN IF NOT EXISTS question_de text;
UPDATE ops.term SET trigger_regex = 'fluktuation', ask_when = 'always' WHERE term = 'fluktuation' AND trigger_regex IS NULL;
DELETE FROM ops.term WHERE term IN ('beschaeftigte', 'monat') AND trigger_regex IS NULL;   -- replaced below (were never asked)
INSERT INTO ops.term (term, reading_id, label_de, definition_de, params, is_default, always_ask, sort, trigger_regex, resolve_regex, ask_when, question_de) VALUES
('personen', 'vvh', 'Beschäftigungsverhältnisse', 'Zählregel Z1: Verhältnisse, nicht Personen – wer zwei Jobs hat, zählt zweimal.', '{"measure": "bestand"}', true, false, 1,
 '\b(menschen|leute|arbeitnehmer(innen)?|erwerbst(ä|ae)tige|köpfe|koepfe|beschäftigte personen)\b', '\b(verhältnis|verhaeltnis|vvh)', 'always', '„{wort}“ – Verhältnisse oder Personen?'),
('personen', 'personen', 'Personen', 'Jede PERSON_ID einmal, unabhängig von der Zahl ihrer Verhältnisse.', '{"measure": "personen"}', false, false, 2,
 NULL, NULL, 'always', NULL),
('personen', 'beides', 'Beides nebeneinander', 'Zuerst Verhältnisse; Personen als Folgefrage.', '{"measure": "bestand", "note": "Personen als Folgefrage: „und als Personen?“"}', false, false, 3,
 NULL, NULL, 'always', NULL),
('entwicklung', 'vormonat', 'gegenüber dem Vormonat', 'Veränderung zum Vormonat, absolut und in Prozent.', '{"compare": "prev"}', true, false, 1,
 '\b(entwicklung|entwickelt|ver(ä|ae)ndert|ver(ä|ae)nderung|gestiegen|gesunken|anstieg|r(ü|ue)ckgang|wachstum|zugenommen|abgenommen)', '(vormonat|vorjahr|zeitreihe|seit|bis|verlauf|20[0-9]{2}-[0-9]{2}.*20[0-9]{2}-[0-9]{2})', 'single_month', '„Entwicklung“ – im Vergleich wozu?'),
('entwicklung', 'vorjahr', 'gegenüber dem Vorjahresmonat', 'Veränderung zum selben Monat des Vorjahres (ab 08/2025 möglich).', '{"compare": "year"}', false, false, 2, NULL, NULL, 'single_month', NULL),
('entwicklung', 'zeitreihe', 'Zeitreihe seit Beginn', 'Alle Monate 08/2024 bis zum gefragten Monat.', '{"compare": "series"}', false, false, 3, NULL, NULL, 'single_month', NULL),
('jahr', 'durchschnitt', 'Jahresdurchschnitt', 'Mittelwert der Monatsstände (Stichtage) des Jahres; nur vorhandene Monate.', '{"year": "mean"}', true, false, 1,
 '\b(im jahr|jahres|20(24|25|26))\b', '(monat|zeitreihe|entwicklung|verlauf|je monat|durchschnitt|dezember|jahresende|fluktuation|zug(ä|ae)nge|abg(ä|ae)nge|jänner|januar|februar|märz|april|mai|juni|juli|august|september|oktober|november|[0-9]{1,2}/20)', 'year_only', 'Ein Jahr – welcher Wert ist gemeint?'),
('jahr', 'dezember', 'Stand am Jahresende', 'Stichtag 31.12. des Jahres (bzw. letzter vorhandener Monat).', '{"year": "last"}', false, false, 2, NULL, NULL, 'year_only', NULL),
('jahr', 'monate', 'Alle Monatswerte', 'Jeden Monat des Jahres einzeln (Zeitreihe).', '{"year": "all"}', false, false, 3, NULL, NULL, 'year_only', NULL),
('kategorie', 'mit_fd', 'mit freien Dienstverträgen', 'Arbeiter = ArbeiterDV + ArbeiterFD, Angestellte = AngestellteDV + AngestellteFD (wie im Beispielbericht).', '{"kategorie": "mit_fd"}', true, false, 1,
 '\b(arbeiter|angestellte)', '(dienstvertr|\bfd\b|\bdv\b|qualifikation|freie|kategorie)', 'always', '„Arbeiter/Angestellte“ – mit oder ohne freie Dienstverträge?'),
('kategorie', 'nur_dv', 'nur Dienstverträge', 'Nur ArbeiterDV bzw. AngestellteDV.', '{"kategorie": "nur_dv"}', false, false, 2, NULL, NULL, 'always', NULL),
('kategorie', 'getrennt', 'DV und FD getrennt', 'Alle fünf Qualifikationen einzeln ausweisen.', '{"kategorie": "getrennt"}', false, false, 3, NULL, NULL, 'always', NULL),
('oenace_bruch', 'getrennt', 'Getrennt nach Version', 'Bis 12/2024 ÖNACE 2008, ab 01/2025 ÖNACE 2025 – Abschnitte mit gleichem Buchstaben sind nicht immer vergleichbar.', '{"oenace_period": "all"}', true, false, 1,
 '\b(wirtschaftszweig|wirtschaftsbereich|branche|(ö|oe)nace|sektor|abschnitt)', '(2008|2025-|ab 2025|bis 2024|nur ö|getrennt)', 'oenace_break', 'Der Zeitraum überspannt den ÖNACE-Wechsel 2008 → 2025 (01/2025). Wie vergleichen?'),
('oenace_bruch', 'nur_2025', 'Nur ÖNACE 2025', 'Nur Monate ab 01/2025.', '{"oenace_period": "2025"}', false, false, 2, NULL, NULL, 'oenace_break', NULL),
('oenace_bruch', 'nur_2008', 'Nur ÖNACE 2008', 'Nur Monate bis 12/2024.', '{"oenace_period": "2008"}', false, false, 3, NULL, NULL, 'oenace_break', NULL),
('alter', 'einzeljahre', 'Einzelne Altersjahre', 'Alter in vollendeten Jahren am Stichtag (Z5), jedes Jahr einzeln.', '{"age": "alter"}', true, false, 1,
 '\b(alter|altersverteilung|altersstruktur|alterspyramide)\b', '(gruppe|jahrgang|einzel|5-jahr|10-jahr|f(ü|ue)nfjahr|zehnjahr)', 'always', '„Alter“ – in welcher Gliederung?'),
('alter', 'fuenfjahre', '5-Jahres-Gruppen', 'bis 14, 15–19, 20–24 … 70–74, 75 u. mehr, unbekannt.', '{"age": "altersgruppe"}', false, false, 2, NULL, NULL, 'always', NULL),
('alter', 'zehnjahre', '10-Jahres-Gruppen', 'bis 14, 15–24, 25–34 … 65–74, 75 u. mehr, unbekannt.', '{"age": "altersgruppe10"}', false, false, 3, NULL, NULL, 'always', NULL),
('monat', 'stichtag', 'Stichtag Monatsletzter', 'Regelwerk basis: Verhältnisse am Monatsletzten (Fachbeschreibung Z2).', '{"rule_set": "basis"}', true, false, 1,
 '\b(im|für|fuer) (jänner|januar|februar|märz|maerz|april|mai|juni|juli|august|september|oktober|november|dezember)', '(stichtag|ganze[sn]? monat|monatsletzt)', 'both_rule_sets', '„im Monat“ – am Stichtag oder im ganzen Monat?'),
('monat', 'ganzes_monat', 'ganzes Monat', 'Regelwerk auftraege: Verhältnisse mit mindestens einem Tag im Monat (Änderungsauftrag 2).', '{"rule_set": "auftraege"}', false, false, 2, NULL, NULL, 'both_rule_sets', NULL),
('monat', 'beide', 'Beide nebeneinander', 'Zuerst Stichtag; „ganzes Monat“ als Folgefrage.', '{"rule_set": "basis"}', false, false, 3, NULL, NULL, 'both_rule_sets', NULL)
ON CONFLICT (term, reading_id) DO NOTHING;
UPDATE ops.term SET question_de = '„Fluktuation“ – welche Lesart ist gemeint?' WHERE term = 'fluktuation' AND question_de IS NULL;

-- look-ups of one VVH across deliveries (option "aus früherer Lieferung ergänzen")
CREATE INDEX IF NOT EXISTS segment_vvh_delivery ON store.segment (vvh_id, delivery);

-- SW-06: every Rückfrage offers exactly three readings; 'Wechsel von Personen' is answered by the feasibility check (no employer ID)
DELETE FROM ops.term WHERE term = 'fluktuation' AND reading_id = 'd';

-- SW-07: Personen and Zu-/Abgänge are recounted on the treated record set → the copy needs the person.
ALTER TABLE work.dq_copy ADD COLUMN IF NOT EXISTS person_id text;
