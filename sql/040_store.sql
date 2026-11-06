-- Versioned store: one row per delivered record and delivery, typed, with problem flags.
-- Built by `python -m statagent bestand` from roh.lieferung (which stays unchanged).
-- Raw values (…_raw and the code columns) are kept next to the interpreted ones.
CREATE SCHEMA IF NOT EXISTS store;

-- ISO date (JJJJ-MM-TT) or NULL if invalid, e.g. month 13 (DQ-05). Never raises an error.
-- STABLE (not IMMUTABLE) because text::date is STABLE; this lets PostgreSQL inline the function.
CREATE OR REPLACE FUNCTION store.iso_date(t text) RETURNS date
LANGUAGE sql STABLE PARALLEL SAFE AS $$
  SELECT CASE
    WHEN t IS NULL OR t !~ '^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$' THEN NULL
    WHEN substr(t, 1, 4) = '0000' THEN NULL
    WHEN substr(t, 9, 2) <= '28' THEN t::date                    -- fast path: always a valid day
    WHEN substr(t, 9, 2)::int > extract(day FROM make_date(substr(t, 1, 4)::int, substr(t, 6, 2)::int, 1)
                                               + interval '1 month - 1 day')::int THEN NULL
    ELSE t::date
  END
$$;

CREATE TABLE IF NOT EXISTS store.segment (
  delivery        text NOT NULL,              -- delivery JJJJ-MM
  vvh_id          text NOT NULL,              -- delivered field names kept for the codes: vvh_id, person_id, qual, oenace, bundesland
  person_id       text,
  birth_date_raw  text,                       -- GEBURTSDATUM as delivered
  sex             text,                       -- GESCHLECHT as delivered
  begin_raw       text,                       -- BEGINN as delivered
  end_raw         text,                       -- ENDE as delivered
  qual            text,                       -- as delivered
  oenace          text,                       -- as delivered (mapping to klass_oenace via quellzuordnung)
  bundesland      text,                       -- as delivered
  copy_no         integer NOT NULL,           -- 1 = first occurrence; > 1 = exact duplicate (DQ-03)
  birth_date      date,                       -- NULL if invalid (DQ-05)
  birth_year      integer,                    -- year part, also for invalid dates
  begin_date      date,                       -- after approved reading rules (R-DQ01)
  end_date        date,                       -- after approved reading rules (R-DQ01); NULL = open
  effective_end   date,                       -- after approved segment rules (R-DQ09, R-DQ10); NULL = open
  counted         boolean NOT NULL,           -- false for duplicate copies once R-DQ03 is approved
  problems        text[] NOT NULL DEFAULT '{}',  -- detected problems (independent of rules)
  rules           text[] NOT NULL DEFAULT '{}',  -- rules applied to this row
  run_id          bigint NOT NULL
);
-- Derived data, always rebuildable from roh.lieferung: no WAL needed.
ALTER TABLE store.segment SET UNLOGGED;
CREATE INDEX IF NOT EXISTS segment_delivery_vvh ON store.segment (delivery, vvh_id);
CREATE INDEX IF NOT EXISTS segment_delivery_person ON store.segment (delivery, person_id);

-- Delivery profile (= matrix in Problems.md §2.1), written by every store build.
CREATE TABLE IF NOT EXISTS store.profile (
  delivery  text NOT NULL,
  metric    text NOT NULL,
  value     numeric NOT NULL,
  run_id    bigint NOT NULL,
  PRIMARY KEY (delivery, metric)
);
