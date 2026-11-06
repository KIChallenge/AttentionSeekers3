-- Rohdaten: so wie geliefert, alle Felder als Text
CREATE SCHEMA roh;
CREATE TABLE roh.lieferung (
  lieferung    text NOT NULL,   -- Berichtsmonat der Lieferung, JJJJ-MM
  vvh_id       text,
  person_id    text,
  geburtsdatum text,
  geschlecht   text,
  beginn       text,
  ende         text,
  qual         text,
  oenace       text,
  bundesland   text
);
CREATE TABLE roh.lieferung_import (LIKE roh.lieferung);
ALTER TABLE roh.lieferung_import DROP COLUMN lieferung;
CREATE TABLE roh.ladeprotokoll (lieferung text PRIMARY KEY, datei text, zeilen bigint, geladen_am timestamptz DEFAULT now());

-- Klassifikationen
CREATE SCHEMA klassifikation;
CREATE TABLE klassifikation.oenace_2008  (code text PRIMARY KEY, bezeichnung text);
CREATE TABLE klassifikation.oenace_2025  (code text PRIMARY KEY, bezeichnung text);
CREATE TABLE klassifikation.bundesland   (code text PRIMARY KEY, bezeichnung text);
CREATE TABLE klassifikation.geschlecht   (code text PRIMARY KEY, bezeichnung text);
CREATE TABLE klassifikation.qualifikation(code text PRIMARY KEY, bezeichnung text, beschaeftigungskategorie text, freier_dienstvertrag text);
