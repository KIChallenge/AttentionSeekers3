"""Calibration test: every number of beispielbericht_2024-08.xlsx recomputed from stat_beschaeftigte (task: "zum Eichen").

The expected values are read from roh.cell (the example report as delivered, SHA-256 registered); the actual values
are sums over stat_beschaeftigte (rule set 'basis', Stichtag 31.08.2024). Tables:
  Tab1   total, Männer/Frauen, Arbeiter / Angestellte / Beamte (FD included, Erläuterungen)
  Tab2   by Bundesland × (total, Arbeiter, Angestellte, Beamte) × sex
  Tab3   Österreich by ÖNACE section × (total, Arbeiter, Angestellte und Beamte) × sex; Tab4–Tab12 the same per Bundesland
  Tab13  by age (bis 14, 15 … 74, 75 u. mehr, unbekannt) × category × sex
"""
import hashlib

from statagent.config import BASE_DIR

REPORT = "beispielbericht_2024-08.xlsx"
MONTH = "2024-08"
OUT = BASE_DIR / "abgabe" / "kalibrierung_2024-08.md"
TAB_REGION = {"Tab3": None, "Tab4": "9", "Tab5": "3", "Tab6": "1", "Tab7": "4", "Tab8": "6", "Tab9": "2", "Tab10": "5",
              "Tab11": "7", "Tab12": "8"}
TAB2_COLUMNS = {3: None, 4: "9", 5: "3", 6: "1", 7: "4", 8: "6", 9: "2", 10: "5", 11: "7", 12: "8", 13: "0"}
CATEGORY = {"Arbeiter": ("ArbeiterDV", "ArbeiterFD"), "Angestellte": ("AngestellteDV", "AngestellteFD"), "Beamte": ("Beamte",),
            "Angestellte und Beamte": ("AngestellteDV", "AngestellteFD", "Beamte")}
SEX_COLUMNS = (None, "M", "W")


def _cells(conn, sheet: str) -> dict[tuple[int, int], str]:
    return {(r, c): v for r, c, v in conn.execute("SELECT row_no, col_no, value FROM roh.cell WHERE path = %s AND sheet = %s",
                                                    (REPORT, sheet)).fetchall()}


def _num(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _age_match(code: str, label_: str) -> bool:
    if label_ == "unbekannt":
        return code == "UNB"
    if code == "UNB" or not code.isdigit():
        return False
    age = int(code)
    if label_ == "bis 14":
        return age <= 14
    if label_ == "75 u. mehr":
        return age >= 75
    return label_.isdigit() and age == int(label_)


# How the example report read birth dates with month 13 (DQ-05): age = reporting year − birth year. The approved R-DQ05
# reads them with day and month swapped instead – both are shown, the official numbers are never changed (SW-10).
EXAMPLE_READING_SQL = """
SELECT region, oenace, geschlecht, qualifikation, alter,
       CASE WHEN (2024 - substr(birth_date_raw, 1, 4)::int) BETWEEN 0 AND 120
            THEN (2024 - substr(birth_date_raw, 1, 4)::int)::text ELSE 'UNB' END AS alter_beispiel
FROM store.month_record
WHERE rule_set = %s AND month = %s AND birth_date_raw ~ '^[0-9]{4}-13-'"""


def calibrate(conn, rule_set: str = "basis") -> dict:
    rows = conn.execute("""SELECT region, oenace, geschlecht, qualifikation, alter, wert FROM stat_beschaeftigte
                           WHERE regelwerk = %s AND stand = %s""", (rule_set, f"Lieferung {MONTH}")).fetchall()
    if not rows:
        raise ValueError(f"Kein Ergebnis für {MONTH} im Regelwerk {rule_set} – zuerst `lauf --lieferung {MONTH}`")
    result = _compare(conn, rows, rule_set)
    if result["mismatches"]:
        # same official records, only the month-13 birth dates read like the example report (computed here, nothing stored)
        dq05 = conn.execute(EXAMPLE_READING_SQL, (rule_set, MONTH)).fetchall()
        alt = list(rows) + [(r, o, g, q, a, -1) for r, o, g, q, a, _ in dq05] + [(r, o, g, q, b, 1) for r, o, g, q, _, b in dq05]
        other = _compare(conn, alt, rule_set)
        result["example_reading"] = {"records": len(dq05), "mismatches": len(other["mismatches"])}
        result["explained"] = not other["mismatches"] and all(m[0] == "Tab13" for m in result["mismatches"])
    else:
        result["example_reading"], result["explained"] = None, False
    return result


def status(result: dict) -> str:
    if result["ok"]:
        return "bestanden"
    if result.get("explained"):
        return "bestanden – Abweichungen vollständig durch R-DQ05 erklärt"
    return "nicht bestanden"


def _compare(conn, rows, rule_set: str) -> dict:

    def value(region=None, oenace=None, sex=None, cat=None, age=None, classified=False):
        quals = CATEGORY[cat] if cat else None
        return int(sum(w for r, o, g, q, a, w in rows
                       if (region is None or r == region) and (oenace is None or o == oenace) and (sex is None or g == sex)
                       and (quals is None or q in quals) and (age is None or _age_match(a, age))
                       and (not classified or o != "UNB")))

    checks = []   # (table, cell, expected, actual, description)

    def check(table, row, col, expected, actual, what):
        if expected is not None:
            checks.append((table, f"Z{row}S{col}", expected, actual, what))

    c = _cells(conn, "Tab1")
    for i, cat in enumerate((None, "Arbeiter", "Angestellte", "Beamte")):
        for j, sex in enumerate(SEX_COLUMNS):
            col = 3 + 3 * i + j
            check("Tab1", 9, col, _num(c.get((9, col))), value(cat=cat, sex=sex), f"{cat or 'Insgesamt'} {sex or 'M+F'}")

    c = _cells(conn, "Tab2")
    for row in range(8, 20):
        i, j = divmod(row - 8, 3)
        cat, sex = (None, "Arbeiter", "Angestellte", "Beamte")[i], SEX_COLUMNS[j]
        for col, region in TAB2_COLUMNS.items():
            check("Tab2", row, col, _num(c.get((row, col))), value(region=region, cat=cat, sex=sex),
                  f"Bundesland {region or 'Österreich'} {cat or 'Insgesamt'} {sex or 'M+F'}")

    for tab, region in TAB_REGION.items():
        c = _cells(conn, tab)
        for row in range(10, 34):
            label_ = c.get((row, 2), "").strip()
            if row == 10:
                kw = {}
            elif row == 11:
                kw = {"classified": True}
            elif label_ == "Wirtschaftszweig unbekannt":
                kw = {"oenace": "UNB"}
            elif label_:
                kw = {"oenace": label_}
            else:
                continue
            for i, cat in enumerate((None, "Arbeiter", "Angestellte und Beamte")):
                for j, sex in enumerate(SEX_COLUMNS):
                    col = 4 + 3 * i + j
                    check(tab, row, col, _num(c.get((row, col))), value(region=region, cat=cat, sex=sex, **kw),
                          f"{label_ or 'Insgesamt'} {cat or 'Insgesamt'} {sex or 'M+F'} (BL {region or 'Ö'})")

    c = _cells(conn, "Tab13")
    for row in range(10, 74):
        label_ = c.get((row, 2), "").strip()
        if not label_:
            continue
        for i, cat in enumerate((None, "Arbeiter", "Angestellte und Beamte")):
            for j, sex in enumerate(SEX_COLUMNS):
                col = 3 + 3 * i + j
                age = None if label_ == "Insgesamt" else label_
                check("Tab13", row, col, _num(c.get((row, col))), value(cat=cat, sex=sex, age=age), f"Alter {label_} {cat or 'Insgesamt'} {sex or 'M+F'}")

    mismatches = [x for x in checks if x[2] != x[3]]
    return {"cells": len(checks), "mismatches": mismatches, "ok": not mismatches,
            "total": value(), "rule_set": rule_set}


def write_report(conn, result: dict, preview: dict | None = None, preview_rules: tuple = ()) -> str:
    lines = ["# Kalibrierung gegen den Beispielbericht 08/2024", "",
             "Erwartete Werte: `beispielbericht_2024-08.xlsx` wie geliefert (roh.cell, Tab1–Tab13); berechnete Werte: `stat_beschaeftigte` "
             f"(Regelwerk {result['rule_set']}, Stichtag 31.08.2024).", "",
             "| Variante | Zellen | Abweichungen | Ergebnis |", "| --- | ---: | ---: | --- |",
             f"| freigegebene Regeln (amtliche Werte) | {result['cells']} | {len(result['mismatches'])} | {status(result)} |"]
    if result.get("example_reading"):
        er = result["example_reading"]
        lines.append(f"| Lesart des Beispielberichts für Geburtsmonat 13 (Alter = Jahr − Geburtsjahr, {er['records']} Verhältnisse; "
                     f"nur zum Vergleich, nichts gespeichert) | {result['cells']} | {er['mismatches']} | "
                     f"{'bestanden' if not er['mismatches'] else 'nicht bestanden'} |")
    if preview is not None:
        lines.append(f"| Vorschau mit {', '.join(preview_rules)} (vorgeschlagen, zurückgerollt) | {preview['cells']} | {len(preview['mismatches'])} | "
                     f"{'bestanden' if preview['ok'] else 'nicht bestanden'} |")
    lines += ["", f"Insgesamt {result['total']:,} Beschäftigungsverhältnisse.".replace(",", "."), ""]
    if preview is not None and preview["ok"] and result["mismatches"]:
        lines += [f"Alle Abweichungen verschwinden mit {', '.join(preview_rules)}; sie betreffen nur die Altersgliederung (Tab13). "
                  "Die Regel braucht die Freigabe durch eine Person.", ""]
    if result.get("explained"):
        lines += [f"Alle {len(result['mismatches'])} Abweichungen liegen in der Altersgliederung (Tab13) und verschwinden, wenn die "
                  f"{result['example_reading']['records']} Geburtsdaten mit Monat 13 wie im Beispielbericht gelesen werden. Die freigegebene "
                  "Regel R-DQ05 liest sie bewusst mit vertauschtem Tag und Monat (Teamentscheidung, Problems.md DQ-05); Summen und Tab1–Tab12 "
                  "stimmen exakt. Die Kalibrierung gilt damit als bestanden – mit erklärter, dokumentierter Abweichung.", ""]
    if result["mismatches"]:
        lines += ["Abweichungen mit den freigegebenen Regeln:", ""]
    if result["mismatches"]:
        lines += ["| Tabelle | Zelle | Beispielbericht | StatAgent | Differenz | Merkmal |", "| --- | --- | ---: | ---: | ---: | --- |"]
        for tab, cell, exp, act, what in result["mismatches"][:200]:
            lines.append(f"| {tab} | {cell} | {exp} | {act} | {act - exp:+d} | {what} |")
    text = "\n".join(lines) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(text.encode("utf-8"))
    conn.execute("INSERT INTO ops.report (kind, rule_set, month, path, content, sha256) VALUES ('calibration', %s, %s, %s, %s, %s)",
                 (result["rule_set"], MONTH, OUT.relative_to(BASE_DIR).as_posix(), text, hashlib.sha256(text.encode()).hexdigest()))
    return OUT.relative_to(BASE_DIR).as_posix()
