"""Loader: reads every package file unchanged into PostgreSQL.

Replaces ``datenbank/02_laden.sql``, which only runs inside the Linux container (ENV-15), and
also loads the sources that script ignores (ENV-07). Files are only read, never written.

| Source                                   | Target                                              |
| ---------------------------------------- | --------------------------------------------------- |
| lieferungen/lieferung_JJJJ-MM.csv.gz     | roh.lieferung + roh.ladeprotokoll (as 02_laden.sql) |
| klassifikationen/<5 basic>.csv           | klassifikation.* (as 02_laden.sql)                  |
| other delimited .csv / .txt              | roh.text_line (one row per line, fields as array)   |
| .xlsx / .ods                             | roh.cell (+ roh.merged_range for .xlsx)             |
| .pdf                                     | roh.pdf_page (text per page)                        |
| everything else (.sql, .md, LIESMICH)    | registered only                                     |

Every file is registered in roh.file with size and SHA-256. Unchanged files are skipped on
re-runs; ``verify()`` recomputes the checksums to prove that nothing was changed.
"""
import csv
import datetime as dt
import gzip
import hashlib
import io
import re
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from pypdf import PdfReader

from statagent.config import BASE_DIR, connect, setup_logging
from statagent.migration import migrate

AREAS = ["lieferungen", "klassifikationen", "pensionen", "vorlagen", "datenbank"]   # package folders
REFERENCE_FILES = ["beispielbericht_2024-08.xlsx"]
BASIC_CLASSIFICATIONS = ["oenace_2008", "oenace_2025", "bundesland", "geschlecht", "qualifikation"]
SKIP_NAMES = {".DS_Store"}
DOC_NAMES = {"LIESMICH.txt"}
DELIVERY_NAME = re.compile(r"^lieferung_(\d{4}-\d{2})\.csv(\.gz)?$")
EXPECTED_DELIVERY_ROWS = 10_152_292
COPY_CSV = "WITH (FORMAT csv, DELIMITER ';', HEADER true, ENCODING 'UTF8')"


def iter_files():
    """All package data files as (area, path). Folders are walked recursively, so the
    damaged folder name 'Änderungen' (ENV-03) needs no hard-coded path."""
    for area in AREAS:
        for path in sorted((BASE_DIR / area).rglob("*")):
            if path.is_file() and path.name not in SKIP_NAMES:
                yield area, path
    for name in REFERENCE_FILES:
        yield "reference", BASE_DIR / name


def file_format(path: Path) -> str:
    name = path.name.lower()
    for suffix in (".csv.gz", ".csv", ".txt", ".xlsx", ".ods", ".pdf"):
        if name.endswith(suffix):
            return suffix[1:]
    return "other"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def decode(raw: bytes) -> tuple[str, str]:
    """Decode text as UTF-8 if possible, else cp1252 (ÖNACE files, ENV-06)."""
    try:
        return raw.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("cp1252"), "cp1252"


def cell_value(value, data_type: str | None = None) -> tuple[str, str] | None:
    """(type, text) for a spreadsheet value; numbers without float noise, None/NaN skipped."""
    if value is None or (isinstance(value, float) and value != value):
        return None
    if data_type == "f":
        return "f", str(value)
    if isinstance(value, bool):
        return "b", str(value).lower()
    if isinstance(value, int):
        return "n", str(value)
    if isinstance(value, float):
        return "n", str(int(value)) if value.is_integer() else repr(value)
    if isinstance(value, (dt.datetime, dt.date, dt.time, pd.Timestamp)):
        return "d", value.isoformat()
    return "s", str(value)


# --- loaders per format -------------------------------------------------------------------

def load_delivery(cur, path: Path, month: str) -> int:
    """Same steps as 02_laden.sql: staging table, INSERT with the month, load protocol."""
    cur.execute("DELETE FROM roh.lieferung WHERE lieferung = %s", (month,))
    cur.execute("DELETE FROM roh.ladeprotokoll WHERE lieferung = %s", (month,))
    cur.execute("TRUNCATE roh.lieferung_import")
    with cur.copy(f"COPY roh.lieferung_import FROM STDIN {COPY_CSV}") as copy, gzip.open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            copy.write(chunk)
    cur.execute("INSERT INTO roh.lieferung SELECT %s, * FROM roh.lieferung_import", (month,))
    rows = cur.rowcount
    cur.execute("INSERT INTO roh.ladeprotokoll (lieferung, datei, zeilen) VALUES (%s, %s, %s)", (month, path.name, rows))
    cur.execute("TRUNCATE roh.lieferung_import")
    return rows


def load_basic_classification(cur, path: Path, table: str) -> int:
    """Same as 02_laden.sql: COPY the CSV into klassifikation.<table>."""
    cur.execute(f"TRUNCATE klassifikation.{table}")
    with cur.copy(f"COPY klassifikation.{table} FROM STDIN {COPY_CSV}") as copy:
        copy.write(path.read_bytes())
    return cur.execute(f"SELECT count(*) FROM klassifikation.{table}").fetchone()[0]


def load_text_lines(cur, path: Path, rel: str) -> tuple[int | None, str]:
    """Delimited text: one row per line with the fields as delivered (';' separated)."""
    text, encoding = decode(path.read_bytes())
    if path.name in DOC_NAMES or ";" not in text.split("\n", 1)[0]:
        return None, encoding
    rows = 0
    with cur.copy("COPY roh.text_line (path, line_no, fields) FROM STDIN") as copy:
        for i, fields in enumerate(csv.reader(io.StringIO(text, newline=""), delimiter=";", quotechar='"')):
            copy.write_row((rel, i, fields))
            rows += 1
    return rows, encoding


def write_cells(cur, rel: str, cells) -> int:
    count = 0
    with cur.copy("COPY roh.cell (path, sheet, sheet_no, row_no, col_no, cell_ref, type, value) FROM STDIN") as copy:
        for sheet, sheet_no, row, col, typ, text in cells:
            copy.write_row((rel, sheet, sheet_no, row, col, f"{get_column_letter(col)}{row}", typ, text))
            count += 1
    return count


def load_xlsx(cur, path: Path, rel: str) -> int:
    workbook = load_workbook(path, data_only=False)  # not read-only: merged ranges are needed

    def cells():
        for sheet_no, ws in enumerate(workbook.worksheets, start=1):
            for row in ws.iter_rows():
                for c in row:
                    value = cell_value(c.value, c.data_type)
                    if value:
                        yield ws.title, sheet_no, c.row, c.column, *value

    count = write_cells(cur, rel, cells())
    for ws in workbook.worksheets:
        for rng in ws.merged_cells.ranges:
            cur.execute("INSERT INTO roh.merged_range VALUES (%s, %s, %s)", (rel, ws.title, str(rng)))
    return count


def load_ods(cur, path: Path, rel: str) -> int:
    sheets = pd.read_excel(path, sheet_name=None, header=None, engine="odf", dtype=object)

    def cells():
        for sheet_no, (name, frame) in enumerate(sheets.items(), start=1):
            for r, values in enumerate(frame.itertuples(index=False), start=1):
                for c, v in enumerate(values, start=1):
                    value = cell_value(v)
                    if value:
                        yield name, sheet_no, r, c, *value

    return write_cells(cur, rel, cells())


def load_pdf(cur, path: Path, rel: str) -> int:
    pages = PdfReader(path).pages
    for i, page in enumerate(pages, start=1):
        cur.execute("INSERT INTO roh.pdf_page VALUES (%s, %s, %s)", (rel, i, page.extract_text() or ""))
    return len(pages)


def load_content(cur, area: str, path: Path, fmt: str, rel: str) -> tuple[int | None, str | None]:
    """Dispatch by format; returns (loaded units, encoding)."""
    if fmt in ("csv.gz", "csv") and (m := DELIVERY_NAME.match(path.name)):
        return load_delivery(cur, path, m.group(1)), "utf-8"
    if fmt == "csv" and area == "klassifikationen" and path.parent == BASE_DIR / area and path.stem in BASIC_CLASSIFICATIONS:
        return load_basic_classification(cur, path, path.stem), "utf-8"
    if fmt in ("csv", "txt"):
        return load_text_lines(cur, path, rel)
    if fmt == "xlsx":
        return load_xlsx(cur, path, rel), None
    if fmt == "ods":
        return load_ods(cur, path, rel), None
    if fmt == "pdf":
        return load_pdf(cur, path, rel), None
    return None, None


# --- commands ------------------------------------------------------------------------------

def load(force: bool = False) -> None:
    """Load every package file that is new or changed (all files with `force`)."""
    log = setup_logging("laden")
    with connect(autocommit=True) as conn:
        migrate(conn)
        known = dict(conn.execute("SELECT path, sha256 FROM roh.file").fetchall())
        for area, path in iter_files():
            rel, fmt, checksum = path.relative_to(BASE_DIR).as_posix(), file_format(path), sha256(path)
            if not force and known.get(rel) == checksum:
                log.info("unchanged, skipped: %s", rel)
                continue
            with conn.transaction(), conn.cursor() as cur:
                cur.execute("DELETE FROM roh.file WHERE path = %s", (rel,))
                cur.execute("INSERT INTO roh.file (path, area, format, size_bytes, sha256) VALUES (%s, %s, %s, %s, %s)",
                            (rel, area, fmt, path.stat().st_size, checksum))
                units, encoding = load_content(cur, area, path, fmt, rel)
                cur.execute("UPDATE roh.file SET units = %s, encoding = %s WHERE path = %s", (units, encoding, rel))
            log.info("loaded: %s (%s)", rel, "registered only" if units is None else f"{units:,} units")
        log.info("creating indexes and running ANALYZE …")
        conn.execute("CREATE INDEX IF NOT EXISTS lieferung_lieferung_idx ON roh.lieferung (lieferung)")
        conn.execute("CREATE INDEX IF NOT EXISTS lieferung_vvh_id_idx ON roh.lieferung (vvh_id)")
        conn.execute("ANALYZE roh.lieferung")
        total = conn.execute("SELECT coalesce(sum(zeilen), 0) FROM roh.ladeprotokoll").fetchone()[0]
        log.info("done: %s deliveries, %s rows (expected %s)",
                 conn.execute("SELECT count(*) FROM roh.ladeprotokoll").fetchone()[0], f"{total:,}", f"{EXPECTED_DELIVERY_ROWS:,}")


def verify() -> bool:
    """Integrity check: files unchanged since loading, and delivery rows complete."""
    log = setup_logging("pruefen")
    ok = True
    with connect() as conn:
        registered = dict(conn.execute("SELECT path, sha256 FROM roh.file").fetchall())
        on_disk = {path.relative_to(BASE_DIR).as_posix(): path for _, path in iter_files()}
        for rel in sorted(set(registered) | set(on_disk)):
            if rel not in on_disk:
                log.error("missing on disk: %s", rel); ok = False
            elif rel not in registered:
                log.error("not loaded yet: %s", rel); ok = False
            elif sha256(on_disk[rel]) != registered[rel]:
                log.error("CHANGED since loading: %s", rel); ok = False
        rows = conn.execute("""
            SELECT p.lieferung, p.zeilen, count(l.*) FROM roh.ladeprotokoll p
            LEFT JOIN roh.lieferung l USING (lieferung) GROUP BY 1, 2 ORDER BY 1""").fetchall()
        for month, logged, actual in rows:
            if logged != actual:
                log.error("delivery %s: protocol %s rows, table %s rows", month, logged, actual); ok = False
        total = sum(r[2] for r in rows)
        if total != EXPECTED_DELIVERY_ROWS:
            log.error("deliveries total %s rows, expected %s", f"{total:,}", f"{EXPECTED_DELIVERY_ROWS:,}"); ok = False
        log.info("%s files checked, %s deliveries, %s rows → %s", len(on_disk), len(rows), f"{total:,}", "OK" if ok else "PROBLEMS FOUND")
    return ok
