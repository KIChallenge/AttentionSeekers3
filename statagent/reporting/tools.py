"""Deterministic statistics tools – the only source of numbers for the web UI, the dashboard, the chat and the agents.

Every tool returns the same envelope (PRD §8):
  {columns, rows, sql, definition, evidence: {deliveries, runs, rules, klass_versions}, warnings, numbers}
- `sql` is the exact query that produced the rows (parameters inlined from validated values, so it can be re-run).
- `definition` names the reading that was used (Verhältnisse/Personen, Stichtag/Monat, ÖNACE version, rule set).
- `numbers` lists every number of the result; the claim check (statagent/reporting/claims.py) only lets text pass whose
  numbers appear here.
Inputs are validated against whitelists and patterns; values never reach SQL as raw text from a user or a model.
"""
import datetime as dt
import re

from statagent.core.labels import rule_set_label
from statagent.etl.store import month_bounds

MONTH = re.compile(r"^20\d{2}-(0[1-9]|1[0-2])$")
CODE = re.compile(r"^[A-Za-z0-9 ._+-]{1,20}$")
RULE_SETS = {"basis": "Fachbeschreibung (Stichtag Monatsletzter, Kategorien laut Qualifikation)",
             "auftraege": "nach den Änderungsaufträgen 1 + 2 (ganzes Monat, Arbeiter/Angestellte/Beamte)"}
DIMENSIONS = {
    "region": ("region", "Bundesland (Arbeitsort)"),
    "oenace": ("oenace", "Wirtschaftszweig (ÖNACE-Abschnitt)"),
    "geschlecht": ("geschlecht", "Geschlecht"),
    "qualifikation": ("qualifikation", "Beschäftigungskategorie (Qualifikation)"),
    "kategorie": ("CASE WHEN qualifikation LIKE 'Arbeiter%%' THEN 'Arbeiter' WHEN qualifikation LIKE 'Angestellte%%' THEN 'Angestellte' "
                  "ELSE qualifikation END", "Arbeiter / Angestellte / Beamte (DV + FD)"),
    "alter": ("alter", "Alter in vollendeten Jahren"),
    "altersgruppe": ("CASE WHEN alter = 'UNB' THEN 'unbekannt' WHEN alter::int < 15 THEN 'bis 14' WHEN alter::int >= 75 THEN '75 u. mehr' "
                     "ELSE lpad((alter::int / 5 * 5)::text, 2, '0') || '–' || (alter::int / 5 * 5 + 4)::text END",
                     "Altersgruppe (5 Jahre)"),
    "altersgruppe10": ("CASE WHEN alter = 'UNB' THEN 'unbekannt' WHEN alter::int < 15 THEN 'bis 14' WHEN alter::int >= 75 THEN '75 u. mehr' "
                       "ELSE ((alter::int - 15) / 10 * 10 + 15)::text || '–' || ((alter::int - 15) / 10 * 10 + 24)::text END",
                       "Altersgruppe (10 Jahre)"),
}
FILTER_COLUMNS = {"region", "oenace", "geschlecht", "qualifikation", "alter"}
MEASURES = {
    "bestand": "Beschäftigungsverhältnisse",
    "personen": "beschäftigte Personen",
    "zugaenge": "Zugänge (neue Verhältnisse gegenüber dem Vormonat)",
    "abgaenge": "Abgänge (beendete Verhältnisse gegenüber dem Vormonat)",
    "fluktuation": "Zugänge + Abgänge gegenüber dem Vormonat",
    "fluktuationsrate": "Fluktuationsrate = Abgänge ÷ Bestand am Ende des Vormonats (in %)",
}
LABEL_SQL = {
    "region": "SELECT code, bezeichnung FROM klass_region WHERE ebene = 'Bundesland' AND gueltig_bis IS NULL",
    "geschlecht": "SELECT code, bezeichnung FROM klass_geschlecht",
    "qualifikation": "SELECT code, bezeichnung FROM klass_qualifikation",
    "alter": "SELECT code, bezeichnung FROM klass_alter WHERE ebene = 'Altersjahr' OR code = 'UNB'",
}


class ToolError(ValueError):
    """Invalid request – shown to the user as a German message, never answered with a guess."""


def _lit(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def render_sql(sql: str, params: dict) -> str:
    """Inline validated parameters for display (the displayed query is runnable as is)."""
    def repl(m):
        v = params[m.group(1)]
        if isinstance(v, (list, tuple)):
            return "ARRAY[" + ", ".join(_lit(x) for x in v) + "]" + ("::text[]" if not v else "")
        return _lit(v)
    return re.sub(r"%\((\w+)\)s", repl, sql).replace("%%", "%")


def _months(conn, rule_set: str) -> list[str]:
    return [r[0] for r in conn.execute("SELECT DISTINCT substr(stand, 11) FROM stat_beschaeftigte WHERE regelwerk = %s ORDER BY 1",
                                      (rule_set,)).fetchall()]


def validate(conn, rule_set: str, months: list[str], dimensions: list[str], filters: dict, measure: str) -> list[str]:
    if rule_set not in RULE_SETS:
        raise ToolError(f"Regelwerk „{rule_set}“ unbekannt – möglich: {', '.join(RULE_SETS)}")
    if measure not in MEASURES:
        raise ToolError(f"Kennzahl „{measure}“ unbekannt – möglich: {', '.join(MEASURES)}")
    for d in dimensions:
        if d not in DIMENSIONS:
            raise ToolError(f"Gliederung „{d}“ unbekannt – möglich: {', '.join(DIMENSIONS)}")
    for k, v in filters.items():
        values = v if isinstance(v, list) else [v]
        if k not in FILTER_COLUMNS and k not in ("kategorie",):
            raise ToolError(f"Filter „{k}“ unbekannt")
        if not values or not all(isinstance(x, str) and CODE.match(x) for x in values):
            raise ToolError(f"Filterwert für {k} ungültig")
    available = _months(conn, rule_set)
    for m in months:
        if not MONTH.match(m):
            raise ToolError(f"Monat „{m}“ hat nicht das Format JJJJ-MM")
    missing = [m for m in months if m not in available]
    if missing:
        raise ToolError(f"nicht vorhanden: für {', '.join(missing)} gibt es im Regelwerk {rule_set_label(rule_set)} kein Ergebnis "
                        f"(gerechnet: {available[0] if available else '–'} bis {available[-1] if available else '–'})")
    return available


def labels(conn, dimension: str, months: list[str]) -> dict[str, str]:
    if dimension == "oenace":
        out = {}
        versions = sorted({"2008" if m <= "2024-12" else "2025" for m in months})
        for v in versions:
            for code, name in conn.execute("SELECT code, bezeichnung FROM klass_oenace WHERE version = %s AND ebene = 'Abschnitt'", (v,)):
                out[code] = name if len(versions) == 1 else out.get(code, name)
        out["NZ"] = "nicht zuordenbar"
        return out
    if dimension in LABEL_SQL:
        out = dict(conn.execute(LABEL_SQL[dimension]).fetchall())
        out["NZ"] = "nicht zuordenbar"
        return out
    return {}


def _filter_sql(filters: dict, params: dict) -> str:
    parts = []
    for i, (k, v) in enumerate(sorted(filters.items())):
        values = v if isinstance(v, list) else [v]
        col = DIMENSIONS["kategorie"][0] if k == "kategorie" else k
        names = []
        for j, x in enumerate(values):
            params[f"f{i}_{j}"] = x
            names.append(f"%(f{i}_{j})s")
        parts.append(f"{col} IN ({', '.join(names)})" if len(names) > 1 else f"{col} = {names[0]}")
    return "".join(f" AND {p}" for p in parts)


def evidence(conn, rule_set: str, months: list[str]) -> dict:
    """Quellennachweis for the months: delivery files + SHA-256, runs + checksums, rules + approver, versions."""
    runs = conn.execute("""SELECT DISTINCT ON (substr(s.stand, 11)) substr(s.stand, 11), r.run_id, r.checksum, s.status, r.rules,
                                  r.finished_at
                           FROM stat_beschaeftigte s JOIN ops.run r ON r.run_id = s.lauf_id
                           WHERE s.regelwerk = %s AND s.stand = ANY(%s) ORDER BY substr(s.stand, 11), r.run_id DESC""",
                        (rule_set, [f"Lieferung {m}" for m in months])).fetchall()
    rule_ids = sorted({x for r in runs for x in (r[4] or [])})
    rules = [dict(id=r[0], title=r[1], approved_by=r[2], approved_at=r[3].isoformat() if r[3] else None, problem=r[4])
             for r in conn.execute("""SELECT rule_id, title, approved_by, approved_at, problem_id FROM ops.rule
                                      WHERE rule_id = ANY(%s) ORDER BY rule_id""", (rule_ids,)).fetchall()]
    files = {m: (p, s) for m, p, s in conn.execute(
        """SELECT substring(path from 'lieferung_(\\d{4}-\\d{2})'), path, sha256 FROM roh.file WHERE area = 'lieferungen'""").fetchall()}
    klass = conn.execute("""SELECT run_id, checksum FROM ops.run WHERE kind = 'classification' AND status = 'done'
                            ORDER BY run_id DESC LIMIT 1""").fetchone()
    return {
        "rule_set": rule_set,
        "deliveries": [{"month": m, "file": files.get(m, (None, None))[0], "sha256": files.get(m, (None, None))[1]} for m in months],
        "runs": [{"month": r[0], "run_id": r[1], "checksum": r[2], "status": r[3], "finished_at": r[5].isoformat() if r[5] else None}
                 for r in runs],
        "rules": rules,
        "klass_versions": sorted({"ÖNACE 2008" if m <= "2024-12" else "ÖNACE 2025" for m in months}),
        "klass_run": {"run_id": klass[0], "checksum": klass[1]} if klass else None,
    }


def _definition(rule_set: str, measure: str, months: list[str], dimensions: list[str], filters: dict) -> str:
    whole = rule_set == "auftraege"
    when = "im ganzen Monat (mind. ein Tag)" if whole else "am Stichtag (Monatsletzter)"
    if len(months) == 1:
        start, ref = month_bounds(months[0])
        period = f"{start:%m/%Y}" if whole else f"Stichtag {ref:%d.%m.%Y}"
    else:
        period = f"{months[0]} bis {months[-1]}"
    unit = "Personen (PERSON_ID einmal gezählt)" if measure == "personen" else "Versicherungsverhältnisse (Zählregel Z1)"
    parts = [f"Definition: {MEASURES[measure]} – {unit} {when}, {period}",
             f"Regelwerk {rule_set_label(rule_set)} ({RULE_SETS[rule_set]}), mit freigegebenen Leseregeln"]
    if "oenace" in dimensions or "oenace" in filters:
        parts.append(", ".join(sorted({"ÖNACE 2008" if m <= "2024-12" else "ÖNACE 2025" for m in months})))
    if "region" in dimensions or "region" in filters:
        parts.append("Bundesland des Arbeitsortes (Wohnort nicht geliefert)")
    if filters:
        parts.append("Filter: " + "; ".join(f"{k} = {', '.join(v if isinstance(v, list) else [v])}" for k, v in sorted(filters.items())))
    return " · ".join(parts)


def query_stat(conn, rule_set: str = "basis", months: list[str] | None = None, dimensions: list[str] | None = None,
               filters: dict | None = None, measure: str = "bestand") -> dict:
    """Values per month (and dimension codes) from stat_beschaeftigte / store.month_record."""
    dimensions, filters = list(dimensions or []), dict(filters or {})
    available = _months(conn, rule_set)
    months = list(months or (available[-1:] if available else []))
    validate(conn, rule_set, months, dimensions, filters, measure)
    params: dict = {"rule_set": rule_set, "stands": [f"Lieferung {m}" for m in months]}
    dim_sql = [DIMENSIONS[d][0] for d in dimensions]
    select_dims = "".join(f", {expr} AS {d}" for d, expr in zip(dimensions, dim_sql))
    group = "".join(f", {i + 2}" for i in range(len(dimensions)))
    where_f = _filter_sql(filters, params)
    warnings = []
    if measure == "bestand":
        sql = (f"SELECT substr(stand, 11) AS monat{select_dims}, sum(wert)::bigint AS wert\nFROM stat_beschaeftigte\n"
               f"WHERE regelwerk = %(rule_set)s AND stand = ANY(%(stands)s) AND variable = 'Beschaeftigungsverhaeltnisse'{where_f}\n"
               f"GROUP BY 1{group}\nORDER BY 1{group}")
    elif measure == "personen":
        sql = (f"SELECT month AS monat{select_dims}, count(DISTINCT person_id)::bigint AS wert\nFROM store.month_record\n"
               f"WHERE rule_set = %(rule_set)s AND month = ANY(%(months)s){where_f}\nGROUP BY 1{group}\nORDER BY 1{group}")
        params["months"] = months
    else:
        prev = {m: _prev(m) for m in months}
        missing = [m for m in months if prev[m] not in available]
        if missing:
            raise ToolError(f"nicht vorhanden: Für {', '.join(missing)} fehlt der Vormonat; Zu- und Abgänge sind erst ab "
                            f"{available[1] if len(available) > 1 else '–'} bestimmbar")
        params["pairs"] = [f"{prev[m]}>{m}" for m in months]
        params["months"] = months
        have = {r[0] for r in conn.execute("SELECT DISTINCT month FROM store.month_flow WHERE rule_set = %s AND month = ANY(%s)",
                                           (rule_set, months)).fetchall()}
        if set(months) - have:
            raise ToolError(f"nicht vorhanden: Zu-/Abgänge für {', '.join(sorted(set(months) - have))} noch nicht berechnet (Lauf fehlt)")
        flow = f"""WITH pairs AS (SELECT split_part(p, '>', 1) AS prev, split_part(p, '>', 2) AS cur FROM unnest(%(pairs)s::text[]) p),
zu AS (SELECT month AS monat{select_dims}, sum(n) AS n FROM store.month_flow
       WHERE rule_set = %(rule_set)s AND kind = 'zu' AND month = ANY(%(months)s){where_f} GROUP BY 1{group}),
ab AS (SELECT month AS monat{select_dims}, sum(n) AS n FROM store.month_flow
       WHERE rule_set = %(rule_set)s AND kind = 'ab' AND month = ANY(%(months)s){where_f} GROUP BY 1{group}),
vb AS (SELECT p.cur AS monat{select_dims}, sum(s.wert) AS n FROM pairs p
       JOIN stat_beschaeftigte s ON s.regelwerk = %(rule_set)s AND s.stand = 'Lieferung ' || p.prev
       WHERE true{where_f} GROUP BY 1{group})"""
        keys = ["monat"] + dimensions
        value = {"zugaenge": "coalesce(zu.n, 0)", "abgaenge": "coalesce(ab.n, 0)",
                 "fluktuation": "coalesce(zu.n, 0) + coalesce(ab.n, 0)",
                 "fluktuationsrate": "round(100.0 * coalesce(ab.n, 0) / nullif(vb.n, 0), 2)"}[measure]
        k = ", ".join(keys)
        sql = (f"{flow},\nk AS (SELECT {k} FROM vb UNION SELECT {k} FROM zu UNION SELECT {k} FROM ab)\n"
               f"SELECT {', '.join('k.' + x for x in keys)}, {value} AS wert\nFROM k LEFT JOIN vb USING ({k}) "
               f"LEFT JOIN zu USING ({k}) LEFT JOIN ab USING ({k})\nORDER BY {', '.join(str(i + 1) for i in range(len(keys)))}")
        affected = {"2025-10": "DQ-02 (Lieferung 2025-10 unvollständig)", "2025-11": "DQ-02 (Vormonat unvollständig)",
                    "2025-03": "DQ-04 (keine freien Dienstverträge)", "2025-04": "DQ-04 (Vormonat ohne FD)"}
        for m in months:
            if m in affected:
                warnings.append(f"{m}: Zu-/Abgänge durch {affected[m]} verzerrt – Lieferfehler, keine reale Fluktuation")
        warnings.append("Jeden Monat enthalten die Zu- und Abgänge rund 200 vermutete Doppelmeldungen (DQ-16), die mit der "
                        "nächsten Lieferung wieder verschwinden.")
    cur = conn.execute(sql, params)
    columns = [c.name for c in cur.description]
    rows = [dict(zip(columns, [float(v) if hasattr(v, "as_integer_ratio") and not isinstance(v, int) else v for v in r]))
            for r in cur.fetchall()]
    shown_sql = render_sql(sql, params)
    names = {d: labels(conn, d, months) for d in dimensions}
    for r in rows:
        for d in dimensions:
            r[f"{d}_label"] = names[d].get(r[d], r[d])
    for m in months:
        if rule_set == "basis" and m == "2025-10":
            warnings.append("10/2025: Lieferung unvollständig (DQ-02) – Wert wie geliefert bzw. mit Annahme R-DQ02, falls freigegeben.")
        if m == "2025-03" and ("qualifikation" in dimensions or "kategorie" in dimensions):
            warnings.append("03/2025: Freie Dienstverträge fehlen in der Lieferung (DQ-04).")
    if "oenace" in dimensions and any(m <= "2024-12" for m in months) and any(m >= "2025-01" for m in months):
        warnings.append("Klassifikationsbruch 01/2025: ÖNACE 2008 → ÖNACE 2025; Abschnitte vor und nach dem Bruch sind nicht direkt vergleichbar.")
    ev = evidence(conn, rule_set, months)
    published = {r["month"]: r["status"] for r in ev["runs"]}
    if any(s != "endgueltig" for s in published.values()):
        warnings.append("Vorläufige Werte: noch nicht von einer Person veröffentlicht.")
    numbers = sorted({r["wert"] for r in rows if r["wert"] is not None})
    return {"tool": "query_stat", "params": {"rule_set": rule_set, "months": months, "dimensions": dimensions, "filters": filters,
                                             "measure": measure},
            "columns": columns + [f"{d}_label" for d in dimensions], "rows": rows, "sql": shown_sql,
            "definition": _definition(rule_set, measure, months, dimensions, filters), "evidence": ev,
            "warnings": list(dict.fromkeys(warnings)), "numbers": numbers, "unit": "%" if measure == "fluktuationsrate" else "Anzahl"}


def _prev(month: str) -> str:
    y, m = map(int, month.split("-"))
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def example_records(conn, rule_set: str, month: str, filters: dict | None = None, limit: int = 5,
                    vvh_ids: list[str] | None = None) -> dict:
    """Example records behind a number: as read (store.month_record) and as delivered (roh.lieferung rows of the VVH)."""
    filters = dict(filters or {})
    validate(conn, rule_set, [month], [], filters, "bestand")
    params = {"rule_set": rule_set, "month": month, "limit": max(1, min(int(limit), 20))}
    where_f = _filter_sql(filters, params)
    if vvh_ids:
        ids_ok = [v for v in vvh_ids if isinstance(v, str) and v.isdigit()][:20]
        if not ids_ok:
            raise ToolError("VVH_ID ungültig")
        params["vvh"] = ids_ok
        params["limit"] = len(ids_ok)
        where_f += " AND vvh_id = ANY(%(vvh)s)"
    sql = (f"SELECT vvh_id, person_id, origin, source_delivery, begin_date, end_date, region, oenace, geschlecht, qualifikation, alter, "
           f"bundesland_raw, oenace_raw, sex_raw, qual_raw, birth_date_raw, problems, rules\nFROM store.month_record\n"
           f"WHERE rule_set = %(rule_set)s AND month = %(month)s{where_f}\nORDER BY cardinality(problems) DESC, length(vvh_id), vvh_id\nLIMIT %(limit)s")
    cur = conn.execute(sql, params)
    cols = [c.name for c in cur.description]
    read = [dict(zip(cols, [x.isoformat() if isinstance(x, dt.date) else x for x in r])) for r in cur.fetchall()]
    ids = [r["vvh_id"] for r in read]
    raw_sql = ("SELECT lieferung, vvh_id, person_id, geburtsdatum, geschlecht, beginn, ende, qual, oenace, bundesland\n"
               "FROM roh.lieferung WHERE lieferung = %(month)s AND vvh_id = ANY(%(ids)s) ORDER BY vvh_id, beginn")
    ids = ids or list(params.get("vvh", []))      # a VVH not counted in the month: still show its delivered rows
    raw_params = {"month": month, "ids": ids}
    cur = conn.execute(raw_sql, raw_params)
    cols2 = [c.name for c in cur.description]
    delivered = [dict(zip(cols2, r)) for r in cur.fetchall()]
    return {"read": read, "delivered": delivered, "sql_read": render_sql(sql, params), "sql_delivered": render_sql(raw_sql, raw_params)}


# --- pension statistic (stat_pensionen, annual averages 2018–2025) ------------------------------------------
PENSION_DIMS = {"geschlecht": "Geschlecht", "pensionsart": "Pensionsart", "versicherungstraeger": "Versicherungsträger"}
PENSION_TOP_CARRIERS = ["PVA", "SVA", "SVB", "SVS", "VAEB", "BVAEB", "VAN"]     # disjoint per year (no sub-areas, no totals)
PENSION_TAB12 = ["ALTER", "GEM", "WIT", "WAI"]
PENSION_TAB13 = ["LVD", "KOR", "LZV", "SA1", "SA2"]


def pension_years(conn) -> list[int]:
    return [r[0] for r in conn.execute("SELECT DISTINCT extract(year FROM zeitraum_von)::int FROM stat_pensionen ORDER BY 1")]


def query_pension(conn, years: list[int] | None = None, dimensions: list[str] | None = None, filters: dict | None = None) -> dict:
    """Annual averages of pensions per year (and sex / type / carrier) from stat_pensionen. Totals are never summed over
    overlapping carriers: without a carrier the computed total PV (all carriers) is used, by carrier only the top carriers."""
    dimensions, filters = list(dimensions or []), {k: (v if isinstance(v, list) else [v]) for k, v in (filters or {}).items()}
    available = pension_years(conn)
    years = sorted({int(y) for y in (years or available[-1:])})
    for d in dimensions:
        if d not in PENSION_DIMS:
            raise ToolError(f"Gliederung „{d}“ gibt es in der Pensionsstatistik nicht – möglich: {', '.join(PENSION_DIMS)}")
    for k, v in filters.items():
        if k not in PENSION_DIMS or not all(isinstance(x, str) and CODE.match(x) for x in v):
            raise ToolError(f"Filter „{k}“ für die Pensionsstatistik ungültig")
    missing = [y for y in years if y not in available]
    if missing:
        raise ToolError(f"nicht vorhanden: Pensionsstatistik für {', '.join(map(str, missing))} nicht geliefert "
                        f"(vorhanden: {available[0]}–{available[-1]})")
    carriers = filters.get("versicherungstraeger") or (PENSION_TOP_CARRIERS if "versicherungstraeger" in dimensions else ["PV"])
    kinds = filters.get("pensionsart") or (PENSION_TAB12 if "pensionsart" in dimensions else ["GES"])
    params = {"years": years, "carriers": carriers, "kinds": kinds}
    where_sex = ""
    if filters.get("geschlecht"):
        params["sex"] = filters["geschlecht"]
        where_sex = " AND geschlecht = ANY(%(sex)s)"
    select_dims = "".join(f", {d}" for d in dimensions)
    group = "".join(f", {i + 2}" for i in range(len(dimensions)))
    sql = (f"SELECT extract(year FROM zeitraum_von)::int AS jahr{select_dims}, sum(wert)::bigint AS wert\nFROM stat_pensionen\n"
           f"WHERE zeitraum_art = 'Jahresdurchschnitt' AND extract(year FROM zeitraum_von) = ANY(%(years)s)\n"
           f"  AND versicherungstraeger = ANY(%(carriers)s) AND pensionsart = ANY(%(kinds)s){where_sex}\n"
           f"GROUP BY 1{group}\nORDER BY 1{group}")
    cur = conn.execute(sql, params)
    cols = [c.name for c in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    names = {"geschlecht": dict(conn.execute("SELECT code, bezeichnung FROM klass_geschlecht").fetchall()),
             "pensionsart": dict(conn.execute("SELECT code, bezeichnung FROM klass_pensionsart").fetchall()),
             "versicherungstraeger": dict(conn.execute("SELECT code, bezeichnung FROM klass_versicherungstraeger").fetchall())}
    for r in rows:
        r["monat"] = str(r["jahr"])                     # the chart/table code uses "monat" as the time axis
        for d in dimensions:
            r[f"{d}_label"] = names[d].get(r[d], r[d])
    kind_txt = ", ".join(names["pensionsart"].get(k, k) for k in kinds)
    carrier_txt = ", ".join(names["versicherungstraeger"].get(c, c) for c in carriers)
    warnings = []
    if any(k in PENSION_TAB13 or k == "VAP" for k in kinds):
        warnings.append("Vorzeitige Alterspensionen sind eine Teilmenge der Alterspensionen (Tabelle 13) – nicht zu den Pensionsarten addieren.")
    if "versicherungstraeger" in dimensions and any(y <= 2019 for y in years) and any(y >= 2020 for y in years):
        warnings.append("Trägerfusion 2020: SVA + SVB → SVS, VAEB → BVAEB – Träger vor und nach 2020 nicht direkt vergleichbar.")
    files = conn.execute("""SELECT path, sha256 FROM roh.file WHERE area = 'pensionen' AND path NOT LIKE '%%LIESMICH%%'
                            AND substring(path from 'pensionen/(\\d{4})/')::int = ANY(%s) ORDER BY path""", (years,)).fetchall()
    return {"tool": "query_pension", "params": {"years": years, "dimensions": dimensions, "filters": filters},
            "columns": cols + [f"{d}_label" for d in dimensions], "rows": rows, "sql": render_sql(sql, params),
            "definition": f"Pensionsstatistik (Jahresdurchschnitt laut Meldungen der Pensionsversicherungsträger) · Pensionsart: {kind_txt}"
                          f" · Träger: {carrier_txt}",
            "evidence": {"pension_files": [{"file": p, "sha256": s} for p, s in files], "deliveries": [], "runs": [], "rules": [],
                         "klass_versions": [], "rule_set": "pensionen"},
            "warnings": warnings, "numbers": sorted({r["wert"] for r in rows if r["wert"] is not None}), "unit": "Anzahl"}
