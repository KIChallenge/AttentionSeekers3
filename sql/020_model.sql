-- Data model per task Anhang B (schema public, German names as prescribed by the task – kept on purpose).
-- stat_<statistik> = data table (long format); shared: description, variables, klass_<begriff>,
-- transitions (Übergänge) and source mappings (Quellzuordnung). Classifications are filled by `klassifikation`.

-- Description per statistic: name, source, type, notes, footnotes.
CREATE TABLE IF NOT EXISTS statistik_beschreibung (
  statistik     text PRIMARY KEY,                 -- e.g. 'beschaeftigte' -> table stat_beschaeftigte
  name          text NOT NULL,
  quelle        text NOT NULL,
  statistiktyp  text NOT NULL CHECK (statistiktyp IN ('Einzeldaten', 'aggregiert')),
  beschreibung  text,
  anmerkungen   text,
  fussnoten     text
);

-- Which dimension uses which classification at which level (and version per reporting period).
CREATE TABLE IF NOT EXISTS statistik_dimension (
  statistik       text NOT NULL REFERENCES statistik_beschreibung,
  dimension       text NOT NULL,                  -- column in stat_<statistik>
  klassifikation  text NOT NULL,                  -- klass_<begriff>
  ebene           text NOT NULL,                  -- e.g. 'Bundesland', 'Abschnitt'
  version         text NOT NULL DEFAULT '-',      -- classification version ('-' = unversioned)
  gueltig_von     date NOT NULL DEFAULT '0001-01-01',  -- reporting periods using this version
  gueltig_bis     date,
  PRIMARY KEY (statistik, dimension, gueltig_von)
);

-- Shared variable table: the variable code is what stat_<statistik>.variable contains.
CREATE TABLE IF NOT EXISTS variable (
  statistik             text NOT NULL REFERENCES statistik_beschreibung,
  variablencode         text NOT NULL,
  variablenbezeichnung  text NOT NULL,
  beschreibung          text NOT NULL,            -- definition
  einheit               text NOT NULL,
  berechnungslogik      text,
  PRIMARY KEY (statistik, variablencode)
);

-- Classification tables: one per concept ("je Begriff nur eine"), versioned and historised.
DO $$
DECLARE begriff text;
BEGIN
  FOREACH begriff IN ARRAY ARRAY['region', 'oenace', 'geschlecht', 'qualifikation', 'alter'] LOOP
    EXECUTE format($t$
      CREATE TABLE IF NOT EXISTS %I (
        version        text NOT NULL DEFAULT '-',   -- e.g. '2008', '2025', 'Stand 2026-01-01'
        code           text NOT NULL,
        bezeichnung    text NOT NULL,
        ebene          text NOT NULL,               -- e.g. 'Abschnitt', 'Bundesland', 'Gemeinde'
        uebergeordnet  text,                        -- parent code within the same version
        gueltig_von    date,
        gueltig_bis    date,
        attribute      jsonb NOT NULL DEFAULT '{}', -- further properties, e.g. Beschäftigungskategorie
        PRIMARY KEY (version, code)
      )$t$, 'klass_' || begriff);
  END LOOP;
END $$;

-- Transitions between versions or states (old code -> new code).
CREATE TABLE IF NOT EXISTS klass_uebergang (
  klassifikation  text NOT NULL,                  -- e.g. 'klass_oenace'
  version_alt     text NOT NULL,
  code_alt        text NOT NULL,
  version_neu     text NOT NULL,
  code_neu        text NOT NULL,
  beziehung       text NOT NULL CHECK (beziehung IN ('1:1', '1:n', 'n:1', 'm:n')),
  gueltig_ab      date,
  quelle          text,                           -- source file / sheet / row
  anmerkung       text,
  PRIMARY KEY (klassifikation, version_alt, code_alt, version_neu, code_neu)
);

-- How a source writes a value and which code it maps to (instead of a second classification).
CREATE TABLE IF NOT EXISTS quellzuordnung (
  quelle          text NOT NULL,                  -- e.g. 'ZVD-Monatslieferung', 'PVA-Meldung'
  merkmal         text NOT NULL,                  -- source field, e.g. 'OENACE'
  quellwert       text NOT NULL,                  -- value as written by the source; '' = empty field
  klassifikation  text NOT NULL,
  version         text NOT NULL,
  code            text NOT NULL,
  gueltig_von     date NOT NULL DEFAULT '0001-01-01',
  gueltig_bis     date,
  regel_id        text,                           -- justification: ops.rule (NULL = straight from the classification file)
  PRIMARY KEY (quelle, merkmal, quellwert, gueltig_von)
);

-- Data table of the employment statistic (long format, one value per row).
-- regelwerk separates the series under the base rules and after the change orders (SPEC-02).
CREATE TABLE IF NOT EXISTS stat_beschaeftigte (
  regelwerk      text NOT NULL DEFAULT 'basis',
  zeitraum_art   text NOT NULL CHECK (zeitraum_art IN ('Stichtag', 'Monat', 'Jahr')),
  zeitraum_von   date NOT NULL,
  zeitraum_bis   date NOT NULL,
  region         text NOT NULL,
  oenace         text NOT NULL,
  geschlecht     text NOT NULL,
  qualifikation  text NOT NULL,
  alter          text NOT NULL,
  variable       text NOT NULL,
  wert           numeric NOT NULL,
  status         text NOT NULL CHECK (status IN ('vorlaeufig', 'endgueltig', 'gesperrt')),
  stand          text NOT NULL,                   -- e.g. 'Lieferung 2025-03'
  lauf_id        bigint,
  PRIMARY KEY (regelwerk, zeitraum_art, zeitraum_von, region, oenace, geschlecht, qualifikation, alter, variable)
);
