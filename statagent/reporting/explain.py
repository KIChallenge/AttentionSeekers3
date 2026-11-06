"""Deterministic explanation of a classification code (Phase 2, task 6).

The German text comes only from klass_*, klass_uebergang, quellzuordnung and ops.rule – no language model.
Agents may rephrase it, but codes, dates, relation types and legal bases come from here.
"""
from statagent.core.labels import RULE_STATUS, label

TABLES = {"region": "klass_region", "oenace": "klass_oenace", "geschlecht": "klass_geschlecht",
          "qualifikation": "klass_qualifikation", "alter": "klass_alter"}
RELATION = {"1:1": "ein alter Code entspricht genau einem neuen (unverändert, umbenannt oder umcodiert)",
            "1:n": "ein alter Code wurde auf mehrere neue aufgeteilt",
            "n:1": "mehrere alte Codes wurden zu einem neuen zusammengelegt",
            "m:n": "Teile mehrerer alter Codes wurden auf mehrere neue umgegliedert"}
ATTRIBUTES = (("code_anzeige", "Code laut Klassifikation"), ("titel", "Amtlicher Titel"), ("kurztitel", "Kurztitel"),
              ("beschaeftigungskategorie", "Beschäftigungskategorie"), ("freier_dienstvertrag", "Freier Dienstvertrag"),
              ("berichtszeile", "Zeile im Monatsbericht"), ("unbekannt", "Ausprägung für fehlende Angaben"),
              ("anmerkung", "Anmerkung"), ("erlaeuterung", "Erläuterung"), ("quelle", "Quelle"))
MAX_LINES = 12
MAX_TEXT = 400


def _rows(conn, sql: str, params) -> list[dict]:
    cur = conn.execute(sql, params)
    return [dict(zip([c.name for c in cur.description], r)) for r in cur.fetchall()]


def _table(klass: str) -> str:
    name = klass.lower().removeprefix("klass_")
    if name not in TABLES:
        raise ValueError(f"Unbekannte Klassifikation {klass!r} – möglich: {', '.join(TABLES)}")
    return TABLES[name]


def _validity(row) -> str:
    valid_from, valid_to = row["gueltig_von"], row["gueltig_bis"]
    if valid_from is None and valid_to is None:
        return "ohne zeitliche Begrenzung"
    if valid_to is None:
        return f"gültig ab {valid_from:%d.%m.%Y}"
    return f"gültig {valid_from:%d.%m.%Y}–{valid_to:%d.%m.%Y}" if valid_from else f"gültig bis {valid_to:%d.%m.%Y}"


def _value(value) -> str:
    if isinstance(value, bool):
        return "ja" if value else "nein"
    text = str(value).replace("\n", " ")
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT].rstrip() + " …"


def _entry(conn, table: str, code: str, version: str, day) -> dict | None:
    """Entry of `code`: same version, or for regions the state valid on `day` (versions are states there)."""
    if table == "klass_region":
        rows = _rows(conn, """SELECT * FROM klass_region WHERE code = %s AND coalesce(gueltig_von, %s) <= %s
                              AND coalesce(gueltig_bis, %s) >= %s ORDER BY gueltig_von DESC LIMIT 1""",
                     (code, day, day, day, day))
    else:
        rows = _rows(conn, f"SELECT * FROM {table} WHERE code = %s AND version = %s", (code, version))
    return rows[0] if rows else None


def _path(conn, table: str, row: dict) -> str:
    parts, current = [], row
    for _ in range(10):
        if not current or not current["uebergeordnet"]:
            break
        current = _entry(conn, table, current["uebergeordnet"], current["version"], row["gueltig_von"])
        if current:
            parts.append(f"{current['ebene']} {current['code']} {current['bezeichnung']}")
    return " › ".join(reversed(parts))


def _children(conn, table: str, row: dict) -> str:
    if table == "klass_region":
        day = row["gueltig_bis"]
        children = _rows(conn, """SELECT ebene, count(*) AS n FROM klass_region WHERE uebergeordnet = %s
                                  AND (CASE WHEN %s::date IS NULL THEN gueltig_bis IS NULL
                                            ELSE gueltig_von <= %s AND coalesce(gueltig_bis, %s) >= %s END)
                                  GROUP BY ebene""", (row["code"], day, day, day, day))
    else:
        children = _rows(conn, f"SELECT ebene, count(*) AS n FROM {table} WHERE uebergeordnet = %s AND version = %s "
                               "GROUP BY ebene", (row["code"], row["version"]))
    return ", ".join(f"{c['n']} × {c['ebene']}" for c in children)


def _mappings(conn, table: str, row: dict) -> list[str]:
    rows = _rows(conn, """SELECT q.quelle, q.merkmal, q.quellwert, q.gueltig_von, q.gueltig_bis, q.regel_id, r.status
                          FROM quellzuordnung q LEFT JOIN ops.rule r ON r.rule_id = q.regel_id
                          WHERE q.klassifikation = %s AND q.version = %s AND q.code = %s
                          ORDER BY q.quelle, q.merkmal, q.regel_id NULLS FIRST, q.quellwert""",
                 (table, row["version"], row["code"]))
    return [f"  Quelle {m['quelle']} schreibt {m['merkmal']} = "
            + (f"„{m['quellwert']}“" if m["quellwert"] else "(leer)")
            + (f" – Regel {m['regel_id']} ({label(RULE_STATUS, m['status'])}"
               f"{'' if m['status'] == 'approved' else ', noch nicht wirksam'})" if m["regel_id"] else " – laut Klassifikationsdatei")
            for m in rows]


def _transitions(conn, table: str, row: dict, direction: str) -> list[str]:
    own, other = ("alt", "neu") if direction == "out" else ("neu", "alt")
    rows = _rows(conn, f"""
        SELECT u.*, k.bezeichnung FROM klass_uebergang u
        LEFT JOIN {table} k ON k.version = u.version_{other} AND k.code = u.code_{other}
        WHERE u.klassifikation = %s AND u.version_{own} = %s AND u.code_{own} = %s
        ORDER BY u.gueltig_ab, u.version_{other}, u.anteil DESC NULLS LAST, u.code_{other}""",
                 (table, row["version"], row["code"]))
    lines, group, n = [], None, 0
    for i, u in enumerate(rows):
        if (u["gueltig_ab"], u[f"version_{other}"]) != group:
            group, n = (u["gueltig_ab"], u[f"version_{other}"]), 0
            head = "geht über in" if direction == "out" else "entstanden aus"
            if table != "klass_region":
                head += f" (Version {u[f'version_{other}']})"
            lines.append(f"  Übergang am {u['gueltig_ab']:%d.%m.%Y} – {head}:")
        n += 1
        if n > MAX_LINES:
            if n == MAX_LINES + 1:
                rest = sum(1 for x in rows[i:] if (x["gueltig_ab"], x[f"version_{other}"]) == group)
                lines.append(f"    … und {rest} weitere")
            continue
        parts = [u["beziehung"]]
        if u["anteil"] is not None:
            parts.append(f"{float(u['anteil']) * 100:.0f} %")
        if u["anmerkung"]:
            parts.append(u["anmerkung"])
        arrow = "→" if direction == "out" else "←"
        lines.append(f"    {arrow} {u[f'code_{other}']} {u['bezeichnung'] or '(nicht in der Klassifikation)'} "
                     f"({u[f'version_{other}']}) · " + " · ".join(parts))
    return lines


def explain(conn, klass: str, code: str, version: str | None = None) -> str:
    """Label, level, validity, hierarchy, attributes, source mappings and transitions of a code (German text)."""
    table = _table(klass)
    sql = f"SELECT * FROM {table} WHERE (code = %s OR attribute->>'code_anzeige' = %s)"
    params: tuple = (code, code)
    if version:
        sql, params = sql + " AND version = %s", params + (version,)
    rows = _rows(conn, sql + " ORDER BY gueltig_von NULLS FIRST, version", params)
    if not rows:
        return f"{table}: Code {code!r}{f' in Version {version}' if version else ''} nicht gefunden."
    lines, relations = [], set()
    for row in rows:
        lines.append(f"{table} {row['version']} · {row['ebene']} {row['code']} – {row['bezeichnung']} · {_validity(row)}")
        if path := _path(conn, table, row):
            lines.append(f"  gehört zu: {path}")
        if children := _children(conn, table, row):
            lines.append(f"  umfasst: {children}")
        attributes = row["attribute"] or {}
        for key, label_ in ATTRIBUTES:
            if key in attributes and not (key == "code_anzeige" and attributes[key] == row["code"]):
                lines.append(f"  {label_}: {_value(attributes[key])}")
        lines += _mappings(conn, table, row)
        transitions = _transitions(conn, table, row, "in") + _transitions(conn, table, row, "out")
        relations |= {r for r in RELATION for line in transitions if f"· {r}" in line}
        lines += transitions + [""]
    if relations:
        lines.append("Beziehungstypen: " + "; ".join(f"{r} = {RELATION[r]}" for r in RELATION if r in relations))
    return "\n".join(lines).rstrip()
