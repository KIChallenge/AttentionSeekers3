"""Pension statistic (Phase 7): parsers for the carrier reports in pensionen/ → stat_pensionen (Anhang B).

The files are read from roh.cell (as loaded, SHA-256 registered); every value keeps its file/sheet/cell (store.pension_cell).
The format family is detected by header text, never by year or position (PEN-02):
  pva_two_row    PVA ≤ 2021: sheets 'Tabelle 12/13', merged group header + sex row (men first)
  pva_one_row    PVA ≥ 2022: sheets 'Pensionsstand' / 'Vorzeitige Alterspensionen', header 'Art – Geschlecht' (women first)
  code_columns   SVA/SVB: JAHR;TRAEGER;GES;GEM_M … with a 'Legende' sheet (sex written M/F or m/w)
  blocks         VAEB/BVAEB: one sheet, blocks 'A. Pensionsstand' / 'B. Vorzeitige Alterspensionen', numbers as text '18.228' (PEN-03)
  long_van       VAN: Pensionsart;Geschlecht;Anzahl; Tabelle 13 'nicht gesondert gemeldet' (PEN-04)
  long_svs       SVS: Jahr;Sparte;Tabelle;Pensionsart;Geschlecht;Anzahl(;Zeitraum) – GW/LW, M/W ≤ 2022; names and m/w ≥ 2023
Codes come only from quellzuordnung (quelle 'PV-Meldung'); unmapped labels stop the build (nothing is silently dropped).
Delivered totals ('Alle', 'Summe', 'GES', '… gesamt', 'Gesamt') are not stored but checked against the sum of the parts.
Computed: carrier totals (PVA, VAEB/BVAEB, SVS), groups PV-UNS / PV-SELB / PV, and pension-type totals GES / VAP.
"""
import hashlib
import re

from statagent.config import connect, setup_logging

SOURCE = "PV-Meldung"
TOTAL_LABELS = {"alle", "summe", "ges", "insgesamt", "gesamt", "pensionen insgesamt", "pensionsversicherungsanstalt gesamt"}
VARIABLE = {12: "Pensionen", 13: "VorzeitigeAlterspensionen"}


class PensionError(RuntimeError):
    pass


def _num(text: str) -> int | None:
    t = str(text).strip()
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", t):     # PEN-03: '18.429' = 18429 (thousands separator, not a decimal)
        return int(t.replace(".", ""))
    if re.fullmatch(r"-?\d+", t):
        return int(t)
    return None


def _sheet(conn, path: str, sheet: str) -> dict[tuple[int, int], tuple[str, str]]:
    return {(r, c): (v, ref) for r, c, v, ref in conn.execute(
        "SELECT row_no, col_no, value, cell_ref FROM roh.cell WHERE path = %s AND sheet = %s", (path, sheet)).fetchall()}


def _year(path: str) -> int:
    return int(re.search(r"/(20\d{2})/", path).group(1))


def _split_art_sex(text: str) -> tuple[str, str]:
    """'Alter – Frauen', 'Alter m', 'GEM_F', 'Witwen/Witwer – Witwer' → (art, sex)."""
    t = text.strip()
    if " – " in t:
        a, s = t.rsplit(" – ", 1)
        return a.strip(), s.strip()
    if "_" in t and re.fullmatch(r"[A-Z0-9]+_[A-Za-z]", t):
        a, s = t.split("_")
        return a, s
    m = re.fullmatch(r"(.+)\s([mw])", t)
    if m:
        return m.group(1).strip(), m.group(2)
    return t, ""


def parse_file(conn, path: str) -> tuple[str, list[dict]]:
    sheets = [r[0] for r in conn.execute("SELECT DISTINCT sheet FROM roh.cell WHERE path = %s", (path,)).fetchall()]
    year = _year(path)
    out = []

    def add(sheet, ref, raw, table, bereich, art, sex, fmt):
        out.append({"path": path, "sheet": sheet, "cell_ref": ref, "raw_value": raw, "value": _num(raw), "jahr": year, "tabelle": table,
                    "bereich_raw": bereich, "art_raw": art, "geschlecht_raw": sex, "format": fmt})

    if {"Tabelle 12", "Tabelle 13"} <= set(sheets):                       # PVA, two-row header
        for sheet, table in (("Tabelle 12", 12), ("Tabelle 13", 13)):
            c = _sheet(conn, path, sheet)
            hdr = next(r for r in range(1, 12) if c.get((r, 1), ("",))[0] == "Bereich")
            groups, cur = {}, None
            for col in range(2, 20):
                if (hdr, col) in c:
                    cur = c[(hdr, col)][0]
                groups[col] = cur
            for r in range(hdr + 2, hdr + 8):
                if (r, 1) not in c:
                    continue
                for col in range(2, 20):
                    if (r, col) in c:
                        sex = c.get((hdr + 1, col), ("",))[0]
                        add(sheet, c[(r, col)][1], c[(r, col)][0], table, c[(r, 1)][0].strip(), groups[col], sex, "pva_two_row")
        return "pva_two_row", out
    if "Pensionsstand" in sheets and "Vorzeitige Alterspensionen" in sheets:   # PVA, one-row header
        for sheet, table in (("Pensionsstand", 12), ("Vorzeitige Alterspensionen", 13)):
            c = _sheet(conn, path, sheet)
            for r in range(2, 10):
                if (r, 1) not in c:
                    continue
                for col in range(2, 20):
                    if (r, col) in c and (1, col) in c:
                        art, sex = _split_art_sex(c[(1, col)][0])
                        add(sheet, c[(r, col)][1], c[(r, col)][0], table, c[(r, 1)][0].strip(), art, sex, "pva_one_row")
        return "pva_one_row", out
    if "Legende" in sheets:                                               # SVA/SVB code columns
        for sheet in [s for s in sheets if s != "Legende"]:
            c = _sheet(conn, path, sheet)
            heads = {col: c[(1, col)][0] for col in range(1, 20) if (1, col) in c}
            table = 13 if any(h.startswith(("LVD", "KOR")) for h in heads.values()) else 12
            for r in range(2, 10):
                if (r, 2) not in c:
                    continue
                for col, h in heads.items():
                    if col <= 2 or (r, col) not in c:
                        continue
                    art, sex = _split_art_sex(h)
                    add(sheet, c[(r, col)][1], c[(r, col)][0], table, c[(r, 2)][0].strip(), art, sex, "code_columns")
        return "code_columns", out
    if len(sheets) == 1:
        sheet = sheets[0]
        c = _sheet(conn, path, sheet)
        first = c.get((1, 1), ("",))[0]
        if c.get((1, 3), ("",))[0] in ("Tabelle",) or c.get((1, 1), ("",))[0] == "Jahr":   # SVS long
            heads = {c[(1, col)][0]: col for col in range(1, 10) if (1, col) in c}
            for r in range(2, 200):
                if (r, heads["Anzahl"]) not in c:
                    continue
                table = 12 if c[(r, heads["Tabelle"])][0].startswith("Pensionsstand") else 13
                add(sheet, c[(r, heads["Anzahl"])][1], c[(r, heads["Anzahl"])][0], table, c[(r, heads["Sparte"])][0].strip(),
                    c[(r, heads["Pensionsart"])][0].strip(), c[(r, heads["Geschlecht"])][0].strip(), "long_svs")
            return "long_svs", out
        if any(v[0].startswith("A. Pensionsstand") for v in c.values()):  # VAEB/BVAEB blocks
            block = None
            for r in range(1, 40):
                label = c.get((r, 1), ("",))[0]
                if label.startswith("A. "):
                    block = 12
                elif label.startswith("B. "):
                    block = 13
                elif label == "Sparte":
                    head = {col: c[(r, col)][0] for col in range(2, 20) if (r, col) in c}
                elif block and label and (r, 2) in c:
                    for col, h in head.items():
                        if (r, col) in c:
                            art, sex = _split_art_sex(h)
                            add(sheet, c[(r, col)][1], c[(r, col)][0], block, label.strip(), art, sex, "blocks")
            return "blocks", out
        if any(v[0] == "Pensionsart" for v in c.values()):               # VAN long
            for r in range(1, 40):
                if (r, 3) in c and c.get((r, 1), ("",))[0] not in ("Pensionsart",) and _num(c[(r, 3)][0]) is not None:
                    add(sheet, c[(r, 3)][1], c[(r, 3)][0], 12, "VAN", c[(r, 1)][0].strip(), c.get((r, 2), ("",))[0].strip(), "long_van")
            if any("nicht gesondert gemeldet" in v[0] for v in c.values()):
                ref = next(v[1] for v in c.values() if "nicht gesondert gemeldet" in v[0])
                add(sheet, ref, "nicht gesondert gemeldet", 13, "VAN", "VAP", "", "long_van")
            return "long_van", out
    raise PensionError(f"{path}: Format nicht erkannt (Blätter {sheets}) – neuer Parser nötig")


def _mapper(conn):
    rows = conn.execute("""SELECT merkmal, quellwert, code, gueltig_von, gueltig_bis FROM quellzuordnung_wirksam WHERE quelle = %s""",
                        (SOURCE,)).fetchall()

    def get(merkmal, value, year):
        import datetime as dt
        day = dt.date(year, 7, 1)
        for m, v, code, von, bis in rows:
            if m == merkmal and v == value and von <= day and (bis is None or day <= bis):
                return code
        return None
    return get


def build(log=None) -> dict:
    log = log or setup_logging("pensionen")
    with connect() as conn, conn.transaction():
        run_id = conn.execute("INSERT INTO ops.run (kind) VALUES ('pension') RETURNING run_id").fetchone()[0]
        files = [r[0] for r in conn.execute("SELECT path FROM roh.file WHERE area = 'pensionen' AND format = 'xlsx' ORDER BY path").fetchall()]
        get = _mapper(conn)
        cells, formats, unmapped, checks = [], {}, [], []
        for path in files:
            fmt, parsed = parse_file(conn, path)
            formats[path] = fmt
            for p in parsed:
                b, a, s = p["bereich_raw"], p["art_raw"], p["geschlecht_raw"]
                is_total = (b or "").strip().lower() in TOTAL_LABELS or (a or "").strip().lower() in TOTAL_LABELS
                p["versicherungstraeger"] = get("Bereich", b, p["jahr"]) if b else None
                p["pensionsart"] = "VAP" if a == "VAP" else get("Pensionsart", a, p["jahr"])
                p["geschlecht"] = get("Geschlecht", s, p["jahr"]) if s else None
                p["is_total"] = is_total or not s
                if not p["is_total"] and (p["versicherungstraeger"] is None or p["pensionsart"] is None or p["geschlecht"] is None):
                    unmapped.append(f"{path} {p['sheet']}!{p['cell_ref']}: Bereich={b!r} Art={a!r} Geschlecht={s!r}")
                cells.append(p)
        if unmapped:
            raise PensionError(f"{len(unmapped)} Werte ohne Quellzuordnung (nichts wird übersprungen): " + "; ".join(unmapped[:8]))
        conn.execute("DELETE FROM store.pension_cell")
        conn.execute("DELETE FROM stat_pensionen")
        with conn.cursor().copy("""COPY store.pension_cell (path, sheet, cell_ref, raw_value, value, jahr, tabelle, bereich_raw, art_raw,
                                   geschlecht_raw, versicherungstraeger, pensionsart, geschlecht, format, run_id) FROM STDIN""") as cp:
            for p in cells:
                cp.write_row((p["path"], p["sheet"], p["cell_ref"], p["raw_value"], p["value"], p["jahr"], p["tabelle"], p["bereich_raw"],
                              p["art_raw"], p["geschlecht_raw"], p["versicherungstraeger"], p["pensionsart"], p["geschlecht"], p["format"], run_id))
        carrier_of = {"PVA-ARB": "PVA", "PVA-ANG": "PVA", "VAEB-EB": "VAEB", "VAEB-BB": "VAEB", "BVAEB-EB": "BVAEB", "BVAEB-BB": "BVAEB",
                      "SVS-GW": "SVS", "SVS-LW": "SVS"}
        # finest delivered cells → stat_pensionen; PVA's 'gesamt' row is a delivered total (checked, not stored)
        for p in cells:
            if p["is_total"] or p["versicherungstraeger"] == "PVA" or p["value"] is None:
                continue
            carrier = carrier_of.get(p["versicherungstraeger"], p["versicherungstraeger"])
            conn.execute("""INSERT INTO stat_pensionen VALUES ('Jahresdurchschnitt', %s, %s, %s, %s, %s, %s, %s, 'endgueltig', %s, %s)""",
                         (f"{p['jahr']}-01-01", f"{p['jahr']}-12-31", p["versicherungstraeger"], p["pensionsart"], p["geschlecht"],
                          VARIABLE[p["tabelle"]], p["value"], f"Meldung {carrier} {p['jahr']}", run_id))
        for p in cells:   # VAN Tabelle 13: not reported ≠ 0
            if p["raw_value"] == "nicht gesondert gemeldet":
                for sex in ("M", "W"):
                    conn.execute("""INSERT INTO stat_pensionen VALUES ('Jahresdurchschnitt', %s, %s, 'VAN', 'VAP', %s, 'VorzeitigeAlterspensionen',
                                    NULL, 'nicht gemeldet', %s, %s)""", (f"{p['jahr']}-01-01", f"{p['jahr']}-12-31", sex, f"Meldung VAN {p['jahr']}", run_id))
        # computed totals: pension-type totals, carriers from areas, groups and PV insgesamt
        conn.execute("""INSERT INTO stat_pensionen
            SELECT zeitraum_art, zeitraum_von, zeitraum_bis, versicherungstraeger, CASE WHEN variable = 'Pensionen' THEN 'GES' ELSE 'VAP' END,
                   geschlecht, variable, sum(wert), 'endgueltig', 'berechnet aus ' || min(stand), %s
            FROM stat_pensionen WHERE status <> 'nicht gemeldet' GROUP BY 1, 2, 3, 4, 6, 7""", (run_id,))
        conn.execute("""INSERT INTO stat_pensionen
            SELECT s.zeitraum_art, s.zeitraum_von, s.zeitraum_bis, k.uebergeordnet, s.pensionsart, s.geschlecht, s.variable, sum(s.wert),
                   'endgueltig', 'berechnet aus den Bereichen ' || extract(year FROM s.zeitraum_von), %s
            FROM stat_pensionen s JOIN klass_versicherungstraeger k ON k.code = s.versicherungstraeger AND k.ebene = 'Versicherungsbereich'
            WHERE s.status <> 'nicht gemeldet' GROUP BY 1, 2, 3, 4, 5, 6, 7""", (run_id,))
        for level in ("Träger", "Gruppe"):
            conn.execute("""INSERT INTO stat_pensionen
                SELECT s.zeitraum_art, s.zeitraum_von, s.zeitraum_bis, k.uebergeordnet, s.pensionsart, s.geschlecht, s.variable, sum(s.wert),
                       'endgueltig', 'berechnet aus den Meldungen ' || extract(year FROM s.zeitraum_von), %s
                FROM stat_pensionen s JOIN klass_versicherungstraeger k ON k.code = s.versicherungstraeger AND k.ebene = %s
                WHERE s.status <> 'nicht gemeldet' GROUP BY 1, 2, 3, 4, 5, 6, 7""", (run_id, level))
        # checks: delivered totals = sum of the parts (per file, table and row/column total)
        for p in cells:
            if not p["is_total"] or p["value"] is None:
                continue
            if p["versicherungstraeger"] == "PVA" and p["pensionsart"] and p["geschlecht"]:      # PVA 'gesamt' row per art × sex
                exp = conn.execute("""SELECT sum(wert) FROM stat_pensionen WHERE versicherungstraeger IN ('PVA-ARB', 'PVA-ANG')
                                      AND extract(year FROM zeitraum_von) = %s AND pensionsart = %s AND geschlecht = %s AND variable = %s""",
                                   (p["jahr"], p["pensionsart"], p["geschlecht"], VARIABLE[p["tabelle"]])).fetchone()[0]
                checks.append((p, exp))
            elif (p["art_raw"] or "").lower() in TOTAL_LABELS and p["versicherungstraeger"]:     # 'Alle'/'Summe'/'GES' column of a row
                code = p["versicherungstraeger"]
                codes = ["PVA-ARB", "PVA-ANG"] if code == "PVA" else [code]
                exp = conn.execute("""SELECT sum(wert) FROM stat_pensionen WHERE versicherungstraeger = ANY(%s) AND extract(year FROM zeitraum_von) = %s
                                      AND variable = %s AND pensionsart NOT IN ('GES', 'VAP')""",
                                   (codes, p["jahr"], VARIABLE[p["tabelle"]])).fetchone()[0]
                checks.append((p, exp))
            elif (p["bereich_raw"] or "").lower() == "gesamt" and p["pensionsart"] and p["geschlecht"]:   # VAEB/BVAEB 'Gesamt' row
                parent = "VAEB" if p["jahr"] < 2020 else "BVAEB"
                exp = conn.execute("""SELECT sum(wert) FROM stat_pensionen WHERE versicherungstraeger IN (%s, %s) AND extract(year FROM zeitraum_von) = %s
                                      AND pensionsart = %s AND geschlecht = %s AND variable = %s""",
                                   (parent + "-EB", parent + "-BB", p["jahr"], p["pensionsart"], p["geschlecht"], VARIABLE[p["tabelle"]])).fetchone()[0]
                checks.append((p, exp))
        failed = [(p, e) for p, e in checks if e is not None and int(e) != p["value"]]
        total = conn.execute("SELECT count(*), md5(string_agg(concat_ws(';', zeitraum_von, versicherungstraeger, pensionsart, geschlecht, variable, wert, status), '|' ORDER BY zeitraum_von, versicherungstraeger, pensionsart, geschlecht, variable)) FROM stat_pensionen").fetchone()
        conn.execute("UPDATE ops.run SET status = %s, finished_at = now(), row_count = %s, checksum = %s, note = %s WHERE run_id = %s",
                     ("done" if not failed else "failed", total[0], total[1],
                      f"{len(files)} Dateien, {len(cells)} Zellen, {len(checks)} Summenprüfungen, {len(failed)} Abweichungen", run_id))
        if failed:
            raise PensionError("Summenprüfung fehlgeschlagen: " + "; ".join(f"{p['path']} {p['cell_ref']} {p['value']} ≠ {e}" for p, e in failed[:5]))
        log.info("pensions: %s files, %s cells, %s stat rows, %s sum checks ok, checksum %s", len(files), len(cells), total[0], len(checks), total[1])
        jumps = conn.execute("""
            WITH t AS (SELECT versicherungstraeger AS t, pensionsart AS a, geschlecht AS g, variable AS v, extract(year FROM zeitraum_von)::int AS y, wert
                       FROM stat_pensionen WHERE status <> 'nicht gemeldet')
            SELECT a.t, a.a, a.g, a.v, a.y, b.wert, a.wert FROM t a JOIN t b ON b.t = a.t AND b.a = a.a AND b.g = a.g AND b.v = a.v AND b.y = a.y - 1
            WHERE b.wert >= 50 AND abs(a.wert - b.wert) > 0.25 * b.wert ORDER BY a.y, a.t""").fetchall()
    return {"run_id": run_id, "files": len(files), "cells": len(cells), "rows": total[0], "checksum": total[1], "sum_checks": len(checks),
            "formats": formats, "jumps": jumps}


def write_report(result: dict) -> str:
    """Prüfbericht der Pensionsstatistik (German): formats, sum checks, explained jumps."""
    from statagent.config import BASE_DIR
    out = BASE_DIR / "abgabe" / "pensionen_pruefbericht.md"
    law = {"SA1": "Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04",
           "SA2": "Schwerarbeitspension § 4 Abs. 3 APG: steigendes Frauenpensionsalter macht Frauen erstmals anspruchsberechtigt – RD-04",
           "LZV": "Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen",
           "VAP": "Summe der vorzeitigen Alterspensionen – folgt den Arten oben"}
    lines = ["# Prüfbericht Pensionsstatistik 2018–2025", "",
             f"Lauf {result['run_id']} · Prüfsumme `{result['checksum']}` · {result['files']} Dateien · {result['cells']} gelesene Zellen · "
             f"{result['rows']} Zeilen in `stat_pensionen` · {result['sum_checks']} Summenprüfungen (gelieferte Summen = Summe der Teile), 0 Abweichungen", "",
             "## 1 Formate (erkannt am Kopf, nicht an Jahr oder Position – PEN-01/02)", "", "| Datei | Format |", "| --- | --- |"]
    lines += [f"| {f} | {fmt} |" for f, fmt in sorted(result["formats"].items())]
    lines += ["", "Zahlen als Text mit Tausenderpunkt (VAEB/BVAEB, z. B. „18.228“) als ganze Zahlen gelesen (PEN-03). VAN meldet keine "
              "vorzeitigen Alterspensionen: Status „nicht gemeldet“, nicht 0 (PEN-04). Geschlecht in 7 Schreibweisen über die Quellzuordnung (PEN-08).", "",
              "## 2 Zeitreihenbruch 2020 (PEN-06, RD-05)", "",
              "SVA + SVB + VAN → SVS, VAEB (+ BVA) → BVAEB (klass_uebergang n:1, gültig ab 01.01.2020). Träger vor und nach 2020 sind nicht direkt "
              "vergleichbar; vergleichbar sind PV insgesamt, PV der Unselbständigen und PV der Selbständigen. Das Notariat ist ab 2020 kein eigener Bereich.", "",
              "## 3 Sprünge > 25 % gegenüber dem Vorjahr", "", "| Jahr | Träger/Bereich | Art | Geschlecht | Vorjahr | Jahr | Einstufung |",
              "| --- | --- | --- | --- | ---: | ---: | --- |"]
    for t, a, g, v, y, before, after in result["jumps"]:
        text = law.get(a, "an die Fachabteilung")
        if a == "SA2" and g == "M":
            text = "Schwerarbeitspension § 4 Abs. 3 APG: Entwicklung nach der Rechtslage (Übergangsrecht) – RD-04"
        cls = ("erklärt – plausibel: " + text) if a in ("SA1", "SA2", "VAP") else ("nicht erklärbar: " + text)
        lines.append(f"| {y} | {t} | {a} | {g} | {int(before):,} | {int(after):,} | {cls} |".replace(",", "."))
    lines += ["", "Synthetische Daten für die KI Challenge – keine amtlichen Zahlen. Erzeugt von `python -m statagent pensionen`."]
    out.parent.mkdir(exist_ok=True)
    out.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    return out.relative_to(BASE_DIR).as_posix()
