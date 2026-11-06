"""Aggregations-Sheet (Fachbeschreibung §5, task step 4) filled into vorlagen/aggregationen_vorlage.xlsx.

- The template is copied, never changed; rows, columns, labels and the "Insgesamt" SUM formulas stay as delivered.
- Values come only from stat_beschaeftigte (= the "Open-Data-File", ENV-11), one column per reporting month.
- Codes the template has no row for (e.g. Geschlecht "UNB", "NZ" nicht zuordenbar) get an extra row "Unbekannt" /
  "nicht zuordenbar" above "Insgesamt" and the SUM range is extended – no value is dropped.
- Rule set 'auftraege' (change order 1): the category sheet gets the rows Arbeiter, Angestellte, Beamte (SPEC-04).
- Check before writing: per month every sheet sums to the same total as stat_beschaeftigte; otherwise nothing is written.
- A sheet "Nachweis" lists run, checksum, status and rules per month, and the check result.
Also written: the Open-Data-File stat_beschaeftigte_<regelwerk>.csv.gz (Anhang B layout, ';').
"""
import csv
import gzip
import hashlib
import io
import shutil

from openpyxl import load_workbook

from statagent.core.labels import RULE_SET
from openpyxl.utils import get_column_letter

from statagent.config import BASE_DIR

TEMPLATE = BASE_DIR / "vorlagen" / "aggregationen_vorlage.xlsx"
OUT_DIR = BASE_DIR / "abgabe"
SHEETS = {  # sheet: (stat column, months filter)
    "Bundesland": ("region", None),
    "Geschlecht": ("geschlecht", None),
    "OENACE_2008": ("oenace", lambda m: m <= "2024-12"),
    "OENACE_2025": ("oenace", lambda m: m >= "2025-01"),
    "Beschaeftigungskategorie": ("qualifikation", None),
}
EXTRA_LABEL = {"UNB": "Unbekannt", "NZ": "nicht zuordenbar", "0": "Bundesland unbekannt"}
CATEGORY_ROWS = [("Arbeiter", "Arbeiter (DV und FD)"), ("Angestellte", "Angestellte (DV und FD)"), ("Beamte", "Beamte")]


class SheetError(RuntimeError):
    pass


def _values(conn, rule_set: str, column: str) -> dict[tuple[str, str], int]:
    return {(m, c): int(v) for m, c, v in conn.execute(
        f"""SELECT substr(stand, 11), {column}, sum(wert) FROM stat_beschaeftigte WHERE regelwerk = %s
            AND variable = 'Beschaeftigungsverhaeltnisse' GROUP BY 1, 2""", (rule_set,)).fetchall()}


def _layout(ws):
    """Header months (col → month), data rows (code → row) and the Insgesamt row of a template sheet."""
    months = {c: ws.cell(1, c).value for c in range(3, ws.max_column + 1) if ws.cell(1, c).value}
    rows, total_row = {}, None
    for r in range(2, ws.max_row + 1):
        code, name = ws.cell(r, 1).value, ws.cell(r, 2).value
        if name == "Insgesamt":
            total_row = r
        elif code is not None:
            rows[str(code)] = r
    return months, rows, total_row


def _set_total(ws, total_row: int, first: int, last: int, months: dict):
    for c in months:
        col = get_column_letter(c)
        ws.cell(total_row, c).value = f"=SUM({col}{first}:{col}{last})"


def _rel(path) -> str:
    try:
        return path.relative_to(BASE_DIR).as_posix()
    except ValueError:
        return str(path)


def build_sheet(conn, rule_set: str = "basis", out_name: str | None = None) -> dict:
    months_done = [r[0] for r in conn.execute("""SELECT DISTINCT substr(stand, 11) FROM stat_beschaeftigte WHERE regelwerk = %s
                                                 ORDER BY 1""", (rule_set,)).fetchall()]
    totals = {m: int(v) for m, v in conn.execute("""SELECT substr(stand, 11), sum(wert) FROM stat_beschaeftigte
                                                    WHERE regelwerk = %s GROUP BY 1""", (rule_set,)).fetchall()}
    out = OUT_DIR / (out_name or f"aggregationen_{rule_set}.xlsx")
    OUT_DIR.mkdir(exist_ok=True)
    tmp = out.with_suffix(".tmp.xlsx")
    shutil.copyfile(TEMPLATE, tmp)
    wb = load_workbook(tmp)
    check, missing_months = {}, set()
    for sheet, (column, keep) in SHEETS.items():
        ws = wb[sheet]
        months, rows, total_row = _layout(ws)
        values = _values(conn, rule_set, column)
        codes_in_data = {c for (m, c) in values if keep is None or keep(m)}
        if sheet == "Beschaeftigungskategorie" and rule_set == "auftraege":
            # change order 1: categories instead of the five Qualifikationen (rows adjusted, SPEC-04)
            first = min(rows.values())
            for r in range(first, total_row + 1):
                for c in range(1, ws.max_column + 1):
                    ws.cell(r, c).value = None
            rows = {}
            for i, (code, name) in enumerate(CATEGORY_ROWS):
                ws.cell(first + i, 1).value, ws.cell(first + i, 2).value = code, name
                rows[code] = first + i
            total_row = first + len(CATEGORY_ROWS)
            ws.cell(total_row, 2).value = "Insgesamt"
            ws.cell(1, 2).value = "Beschäftigungskategorie (nach Änderungsauftrag 1)"
        extra = sorted(codes_in_data - set(rows))
        for code in extra:   # never drop a value: own row above "Insgesamt"
            ws.insert_rows(total_row)
            ws.cell(total_row, 1).value = code
            ws.cell(total_row, 2).value = EXTRA_LABEL.get(code, f"Code {code}")
            rows[code] = total_row
            total_row += 1
        _set_total(ws, total_row, min(rows.values()), total_row - 1, months)
        for c, month in months.items():
            if month not in totals:
                missing_months.add(month)
                continue
            col_sum = 0
            for code, r in rows.items():
                v = values.get((month, code), 0)
                ws.cell(r, c).value = v
                col_sum += v
            check[(sheet, month)] = (col_sum, totals[month])
    bad = {k: v for k, v in check.items() if v[0] != v[1]}
    if bad:
        tmp.unlink(missing_ok=True)
        raise SheetError("Summen stimmen nicht: " + "; ".join(f"{s} {m}: {a} ≠ {b}" for (s, m), (a, b) in sorted(bad.items())[:10]))
    if missing_months:
        tmp.unlink(missing_ok=True)
        raise SheetError(f"Für {', '.join(sorted(missing_months))} gibt es im Regelwerk {RULE_SET.get(rule_set, rule_set)} noch kein Ergebnis – "
                         "zuerst die Monatsläufe ausführen (Regelwerk Aufträge: Seite „Agent“ → „Setze die freigegebenen Aufträge um“; "
                         "Basis: gesamtlauf); ein unvollständiges Sheet wird nicht geschrieben.")

    ws = wb.create_sheet("Nachweis")
    ws.append(["Aggregations-Sheet erzeugt von StatAgent (python -m statagent aggregationen) – Werte aus stat_beschaeftigte"])
    ws.append([f"Regelwerk: {RULE_SET.get(rule_set, rule_set)}", "Prüfung: jedes Blatt ergibt je Monat dieselbe Gesamtzahl wie stat_beschaeftigte",
               f"geprüfte Blatt-Monate: {len(check)}, Abweichungen: 0"])
    ws.append([])
    ws.append(["Berichtsmonat", "Insgesamt", "Lauf", "Prüfsumme", "Status", "angewendete Regeln", "Lieferung SHA-256"])
    runs = conn.execute("""SELECT DISTINCT ON (substr(s.stand, 11)) substr(s.stand, 11), r.run_id, r.checksum, s.status,
                                  array_to_string(r.rules, ', '), f.sha256
                           FROM stat_beschaeftigte s JOIN ops.run r ON r.run_id = s.lauf_id
                           LEFT JOIN roh.file f ON f.path = 'lieferungen/lieferung_' || substr(s.stand, 11) || '.csv.gz'
                           WHERE s.regelwerk = %s ORDER BY substr(s.stand, 11), r.run_id DESC""", (rule_set,)).fetchall()
    for m, run_id, checksum, status, rules, sha in runs:
        ws.append([m, totals[m], run_id, checksum, status, rules, sha])
    ws.column_dimensions["A"].width, ws.column_dimensions["D"].width, ws.column_dimensions["F"].width = 14, 36, 40
    # the template's „Insgesamt“ rows are formulas without a stored result → have Excel/LibreOffice compute them on opening
    # (otherwise previews and some viewers show them empty)
    from openpyxl.workbook.properties import CalcProperties
    wb.calculation = CalcProperties(fullCalcOnLoad=True)
    wb.active = 1                     # open on the first data sheet (Bundesland), not on „Hinweise“ of the template
    wb.save(tmp)
    tmp.replace(out)
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    conn.execute("INSERT INTO ops.report (kind, rule_set, path, sha256) VALUES ('sheet', %s, %s, %s)",
                 (rule_set, _rel(out), digest))
    return {"path": _rel(out), "sha256": digest, "months": len(totals), "checked": len(check),
            "rule_set": rule_set, "totals": totals}


def write_open_data(conn, rule_set: str = "basis") -> dict:
    """stat_beschaeftigte as the Open-Data-File (Anhang B layout, semicolon, gzip)."""
    out = OUT_DIR / f"stat_beschaeftigte_{rule_set}.csv.gz"
    OUT_DIR.mkdir(exist_ok=True)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\n")
    cols = ["zeitraum_art", "zeitraum_von", "zeitraum_bis", "region", "oenace", "geschlecht", "qualifikation", "alter",
            "variable", "wert", "status", "stand"]
    w.writerow(cols)
    n = 0
    for row in conn.execute(f"""SELECT {', '.join(cols)} FROM stat_beschaeftigte WHERE regelwerk = %s
                                ORDER BY zeitraum_von, region, oenace, geschlecht, qualifikation, alter""", (rule_set,)):
        w.writerow([int(v) if c == "wert" else v for c, v in zip(cols, row)])
        n += 1
    with gzip.GzipFile(out, "wb", mtime=0) as f:   # mtime=0: same data → same bytes
        f.write(buf.getvalue().encode("utf-8"))
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    return {"path": _rel(out), "rows": n, "sha256": digest}
