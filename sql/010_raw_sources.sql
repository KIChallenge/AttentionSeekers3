-- Raw storage for every package file besides the monthly deliveries.
-- Complements the delivered datenbank/01_schema.sql (which stays unchanged, incl. its German names).
-- Content is stored exactly as delivered: text rows as field arrays, spreadsheet cells
-- with sheet/cell reference, PDF text per page. Interpretation happens later in views.

-- Registry of all package files with checksum: proves that nothing was changed.
CREATE TABLE IF NOT EXISTS roh.file (
  path        text PRIMARY KEY,           -- path relative to the project folder, '/' separated
  area        text NOT NULL,              -- package folder: lieferungen | klassifikationen | pensionen | vorlagen | datenbank | reference
  format      text NOT NULL,              -- csv.gz | csv | txt | xlsx | ods | pdf | other
  size_bytes  bigint NOT NULL,
  sha256      text NOT NULL,
  encoding    text,                       -- detected text encoding (utf-8 / cp1252), NULL for binary formats
  units       bigint,                     -- loaded rows, cells or pages; NULL = registered only
  loaded_at   timestamptz NOT NULL DEFAULT now()
);

-- Delimited text files (ÖNACE .txt, region .csv, ministerium_vorlage.csv): one row per line.
CREATE TABLE IF NOT EXISTS roh.text_line (
  path     text NOT NULL REFERENCES roh.file ON DELETE CASCADE,
  line_no  integer NOT NULL,              -- 0 = header line
  fields   text[] NOT NULL,               -- fields as delivered (empty string = empty field)
  PRIMARY KEY (path, line_no)
);

-- Spreadsheet cells (.xlsx pensions, example report, template; .ods change lists).
CREATE TABLE IF NOT EXISTS roh.cell (
  path      text NOT NULL REFERENCES roh.file ON DELETE CASCADE,
  sheet     text NOT NULL,                -- sheet name
  sheet_no  integer NOT NULL,             -- 1-based sheet position
  row_no    integer NOT NULL,             -- 1-based row as in Excel
  col_no    integer NOT NULL,             -- 1-based column
  cell_ref  text NOT NULL,                -- A1 reference, e.g. 'B5'
  type      text NOT NULL,                -- s = text, n = number, b = boolean, d = date/time, f = formula
  value     text NOT NULL,                -- value as text (numbers without float noise, formulas with '=')
  PRIMARY KEY (path, sheet, row_no, col_no)
);

-- Merged cell ranges (needed to read the multi-row PVA headers).
CREATE TABLE IF NOT EXISTS roh.merged_range (
  path        text NOT NULL REFERENCES roh.file ON DELETE CASCADE,
  sheet       text NOT NULL,
  cell_range  text NOT NULL,              -- e.g. 'C4:D4'
  PRIMARY KEY (path, sheet, cell_range)
);

-- PDF change lists: extracted text per page (used only as a cross-check).
CREATE TABLE IF NOT EXISTS roh.pdf_page (
  path     text NOT NULL REFERENCES roh.file ON DELETE CASCADE,
  page_no  integer NOT NULL,              -- 1-based
  text     text NOT NULL,
  PRIMARY KEY (path, page_no)
);
