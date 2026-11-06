-- Lädt Klassifikationen und alle Lieferungen beim ersten Start der Datenbank.
DO $$
DECLARE k text; f text; m text; n bigint;
BEGIN
  FOREACH k IN ARRAY ARRAY['oenace_2008','oenace_2025','bundesland','geschlecht','qualifikation'] LOOP
    EXECUTE format($q$COPY klassifikation.%I FROM %L WITH (FORMAT csv, DELIMITER ';', HEADER true, ENCODING 'UTF8')$q$,
                   k, '/daten/klassifikationen/' || k || '.csv');
  END LOOP;
  FOR f IN SELECT x FROM pg_ls_dir('/daten/lieferungen') x WHERE x ~ '^lieferung_\d{4}-\d{2}\.csv(\.gz)?$' ORDER BY x LOOP
    m := substring(f from 'lieferung_(\d{4}-\d{2})');
    TRUNCATE roh.lieferung_import;
    IF f LIKE '%.gz' THEN
      EXECUTE format($q$COPY roh.lieferung_import FROM PROGRAM %L WITH (FORMAT csv, DELIMITER ';', HEADER true, ENCODING 'UTF8')$q$,
                     'gunzip -c /daten/lieferungen/' || f);
    ELSE
      EXECUTE format($q$COPY roh.lieferung_import FROM %L WITH (FORMAT csv, DELIMITER ';', HEADER true, ENCODING 'UTF8')$q$,
                     '/daten/lieferungen/' || f);
    END IF;
    INSERT INTO roh.lieferung SELECT m, * FROM roh.lieferung_import;
    GET DIAGNOSTICS n = ROW_COUNT;
    INSERT INTO roh.ladeprotokoll (lieferung, datei, zeilen) VALUES (m, f, n);
    RAISE NOTICE 'geladen: % (% Zeilen)', m, n;
  END LOOP;
  TRUNCATE roh.lieferung_import;
END $$;
CREATE INDEX ON roh.lieferung (lieferung);
CREATE INDEX ON roh.lieferung (vvh_id);
ANALYZE roh.lieferung;
DO $$ BEGIN RAISE NOTICE 'fertig'; END $$;
