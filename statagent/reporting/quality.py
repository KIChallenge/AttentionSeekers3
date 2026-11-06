"""Dynamic handling of faulty data for a statistic someone asks for (Fragen / chat).

1. detect(): which data problems touch the requested months, dimensions and filters – with the number of affected records.
   The options per problem are data (ops.dq_option, three per problem); the UI adds a free-text field.
2. apply(): the chosen options are applied to a COPY of only the affected records (work.dq_copy, one copy per answer):
   'removed' rows = the official records taken out, 'added' rows = the records as treated (changed codes, carried forward).
   The adjusted statistic = official values (stat_beschaeftigte) − removed + added, grouped like the question.
   store.*, stat_* and the approved rules are never changed; the default option is always the official handling.
3. Free text: mapped deterministically to one of the options (keywords) – or with Azure configured by the model, which may
   only pick an option ID; otherwise it is kept as a note (ops.dq_choice) for the Fachabteilung, never executed as code.
Verhältnisse (bestand): official values − removed + added (adjust). Personen and Zu-/Abgänge/Fluktuation: counted again
on the treated record set with the official definitions (recompute, SW-07); for flows the copy also covers the previous months.
"""
import json
import re

from statagent.reporting import tools

SEVERITY = {"DQ-01": "hoch", "DQ-02": "hoch", "DQ-04": "hoch", "DQ-05": "mittel", "DQ-07": "mittel", "DQ-08": "mittel",
            "DQ-06": "niedrig", "DQ-16": "niedrig"}
TITLE = {"DQ-01": "Lieferung 2025-06: BEGINN und ENDE vertauscht", "DQ-02": "Lieferung 2025-10 unvollständig",
         "DQ-04": "Lieferung 2025-03 ohne freie Dienstverträge", "DQ-05": "Geburtsdatum mit Monat 13 (falsches Datumsformat)",
         "DQ-06": "Geburtsdatum unplausibel (Alter über 110)", "DQ-07": "Veraltete ÖNACE-2003-Codes (DA–DM)",
         "DQ-08": "Bundesland / Wirtschaftszweig leer", "DQ-16": "Verdacht auf Doppelmeldung"}
# records of the affected set (store.month_record m)
AFFECTED = {
    "DQ-05": "m.birth_date_raw ~ '^[0-9]{4}-13-'",
    "DQ-06": "'DQ-06' = ANY(m.problems)",
    "DQ-07": "m.oenace_raw ~ '^D[A-N]$'",
    "DQ-08": "(m.bundesland_raw IS NULL OR m.oenace_raw IS NULL)",
    "DQ-16": "'DQ-16' = ANY(m.problems)",
    "DQ-01": "m.month = '2025-06'",
}
MONTH_PROBLEMS = {"DQ-01": "2025-06", "DQ-02": "2025-10", "DQ-04": "2025-03"}
FREE_TEXT = [  # keyword → action (deterministic interpretation of the free text)
    (r"ausschlie|ausschlie|weglass|nicht (mit)?z(ä|ae)hl|entfern|rausnehm|herausnehm|streich", "exclude"),
    (r"tausch|vertausch|umdreh|monat und tag|tag und monat", "birth_swap"),
    (r"fortschreib|vorliefer|vormonat|(ü|ue)bertrag|aus 2025-0[29]|vom vormonat|feber|februar|september|vorher geliefert", "carry_forward"),
    (r"fr(ü|ue)her|vorher(ige)?|erg(ä|ae)nz|(ü|ue)bernehm|letzte[nr]? bekannte", "fill_from_earlier"),
    (r"ausblend|l(ü|ue)cke|nicht anzeig|monat weg", "hide_month"),
    (r"wie geliefert|original|roh|unver(ä|ae)ndert", "as_delivered"),
    (r"unbekannt|unklar", "age_unknown"),
    (r"mitz(ä|ae)hl|behalten|so lassen|beibehalten|standard", "keep"),
]


# Which option is the OFFICIAL handling depends on the approval state of the rule behind it (rules as data, T3/T7).
OFFICIAL = {"DQ-05": ("R-DQ05", "tausch", "unbekannt"), "DQ-07": ("R-DQ07", "abschnitt_c", None), "DQ-08": ("R-DQ08", "unbekannt", None),
            "DQ-01": ("R-DQ01", "vertauscht", "wie_geliefert"), "DQ-02": ("R-DQ02", "fortschreiben", "wie_geliefert"),
            "DQ-04": ("R-DQ04", "fortschreiben", "wie_geliefert"), "DQ-06": (None, "unbekannt", "unbekannt"),
            "DQ-16": (None, "mitzaehlen", "mitzaehlen")}


def official_option(conn, pid: str) -> str | None:
    rule, if_approved, otherwise = OFFICIAL[pid]
    if rule is None:
        return if_approved
    row = conn.execute("SELECT status, action FROM ops.rule WHERE rule_id = %s", (rule,)).fetchone()
    approved = bool(row and row[0] == "approved" and (pid != "DQ-05" or row[1] == "birth_date_swap"))
    return if_approved if approved else otherwise


def options(conn) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for pid, oid, label, definition, action, default in conn.execute(
            "SELECT problem_id, option_id, label_de, definition_de, action, is_default FROM ops.dq_option ORDER BY problem_id, sort"):
        out.setdefault(pid, []).append({"id": oid, "label": label, "definition": definition, "action": action, "is_default": default})
    return out


def _filter_sql(filters: dict, params: dict, alias: str = "m") -> str:
    sql = tools._filter_sql(filters, params)
    return re.sub(r"\b(region|oenace|geschlecht|qualifikation|alter) (IN|=)", rf"{alias}.\1 \2", sql)


def detect(conn, rule_set: str, months: list[str], dimensions: list[str], filters: dict, measure: str) -> list[dict]:
    """Data problems that affect this statistic, with affected record counts and the handling options."""
    opts = options(conn)
    dims = set(dimensions) | set(filters)
    wanted = []
    if dims & {"alter", "altersgruppe", "altersgruppe10"}:
        wanted += ["DQ-05", "DQ-06"]
    if "oenace" in dims:
        wanted.append("DQ-07")
    if dims & {"region", "oenace"}:
        wanted.append("DQ-08")
    prev_of_requested = {tools._prev(x) for x in months}
    for pid, m in MONTH_PROBLEMS.items():
        # flows (Zu-/Abgänge) of the following month are distorted too: they compare against the defective month
        if m in months or (measure != "bestand" and m in prev_of_requested):
            wanted.append(pid)
    if measure in ("bestand", "zugaenge", "abgaenge", "fluktuation", "fluktuationsrate", "personen"):
        wanted.append("DQ-16")
    issues = []
    for pid in wanted:
        params = {"rule_set": rule_set, "months": months}
        where_f = _filter_sql(filters, params)
        if pid in AFFECTED:
            n = conn.execute(f"""SELECT count(*), array_agg(DISTINCT m.month ORDER BY m.month) FROM store.month_record m
                                 WHERE m.rule_set = %(rule_set)s AND m.month = ANY(%(months)s) AND {AFFECTED[pid]}{where_f}""", params).fetchone()
            count, in_months = n[0], n[1] or []
        else:   # DQ-02 / DQ-04: VVH missing from the delivery that were open in the previous one
            m = MONTH_PROBLEMS[pid]
            fd = "AND p.qual_raw LIKE '%%FD'" if pid == "DQ-04" else ""
            params |= {"m": m, "p": tools._prev(m)}
            count = conn.execute(f"""SELECT count(*) FROM store.month_record p WHERE p.rule_set = %(rule_set)s AND p.month = %(p)s
                                      AND NOT ('DQ-16' = ANY(p.problems)) AND p.end_date IS NULL {fd}{_filter_sql(filters, params, 'p')}
                                      AND NOT EXISTS (SELECT 1 FROM store.segment c WHERE c.delivery = %(m)s AND c.vvh_id = p.vvh_id)""",
                                 params).fetchone()[0]
            in_months = [m] if m in months else []
        if not count:
            continue
        official = official_option(conn, pid)
        # SW-07: every option works for every measure – Personen and Zu-/Abgänge are recounted on the treated copy (recompute)
        o = [dict(x, is_default=(x["id"] == official) if official else x["is_default"], available=True, reason=None)
             for x in opts.get(pid, [])]
        issues.append({"problem_id": pid, "title": TITLE[pid], "severity": SEVERITY[pid], "affected": int(count), "months": in_months,
                       "description": _describe(pid, count, in_months), "options": o,
                       "default": next((x["id"] for x in o if x["is_default"]), None), "free_text": True})
    order = {"hoch": 0, "mittel": 1, "niedrig": 2}
    return sorted(issues, key=lambda i: order[i["severity"]])


def _describe(pid: str, n: int, months: list[str]) -> str:
    f = f"{n:,}".replace(",", ".")
    span = f" ({months[0]}" + (f" bis {months[-1]})" if len(months) > 1 else ")") if months else ""
    return {"DQ-05": f"{f} betroffene Verhältnisse{span}: Monat 13 ist kein gültiges Datum; das Alter hängt von der Behandlung ab.",
            "DQ-06": f"{f} betroffene Verhältnisse{span} mit einem Alter über 110 Jahren.",
            "DQ-07": f"{f} betroffene Verhältnisse{span} mit einem ÖNACE-Code aus 2003.",
            "DQ-08": f"{f} betroffene Verhältnisse{span} ohne Bundesland und Wirtschaftszweig.",
            "DQ-16": f"{f} Verdachtsfälle{span}: neues Verhältnis einer Person mit identischen Merkmalen; fehlt meist in der nächsten Lieferung.",
            "DQ-01": f"Monat 06/2025: {f} Verhältnisse; wie geliefert wären nur 21 aktiv (Spalten vertauscht).",
            "DQ-02": f"{f} in 2025-09 offene Verhältnisse fehlen in der Lieferung 2025-10 vollständig.",
            "DQ-04": f"{f} in 2025-02 offene freie Dienstverträge fehlen in der Lieferung 2025-03."}[pid]


def interpret_free_text(conn, pid: str, text: str, opts: list[dict]) -> tuple[str | None, str]:
    """Free text → option ID (deterministic keywords, or the model choosing only among the option IDs) or a note."""
    t = (text or "").strip().lower()
    if not t:
        return None, ""
    for pattern, action in FREE_TEXT:
        if re.search(pattern, t):
            hit = next((o for o in opts if o["action"] == action or (action == "age_unknown" and o["action"] in ("oenace_unknown",))
                        or (action == "as_delivered" and o["action"] == "keep" and pid in ("DQ-02", "DQ-04", "DQ-16"))), None)
            if hit:
                return hit["id"], f"Freitext verstanden als Option „{hit['label']}“ (Stichwort)"
    from statagent.agents.llm import llm_status
    if llm_status()["configured"]:
        from statagent.agents.llm import LLMUnavailable, chat
        ids = [o["id"] for o in opts] + ["keine"]
        schema = {"type": "function", "function": {"name": "waehle", "description": "Option für die Behandlung fehlerhafter Daten.",
                  "parameters": {"type": "object", "properties": {"option": {"type": "string", "enum": ids}}, "required": ["option"]}}}
        try:
            r = chat([{"role": "system", "content": "Ordne den Wunsch einer der Optionen zu oder 'keine'. Optionen: " +
                       json.dumps([{k: o[k] for k in ("id", "label", "definition")} for o in opts], ensure_ascii=False)},
                      {"role": "user", "content": text}], tools=[schema], purpose=f"quality:{pid}",
                     tool_choice={"type": "function", "function": {"name": "waehle"}})
            oid = r["tool_calls"][0]["arguments"].get("option") if r["tool_calls"] else None
            if oid in ids[:-1]:
                return oid, f"Freitext vom Modell als Option „{next(o['label'] for o in opts if o['id'] == oid)}“ eingeordnet"
        except LLMUnavailable:
            pass
    return None, "Freitext nicht automatisch umsetzbar – als Hinweis gespeichert (Standardbehandlung bleibt)"


COPY_DAYS = 7  # how long a chat copy (work.dq_copy) is kept


def _insert_copy(conn, copy_id, pid, oid, kind, select_sql, params, note=None) -> int:
    cur = conn.execute(f"""INSERT INTO work.dq_copy (copy_id, problem_id, option_id, kind, month, vvh_id, person_id, region, oenace,
                             geschlecht, qualifikation, alter, note)
                           SELECT %(copy_id)s, %(pid)s, %(oid)s, %(kind)s, month, vvh_id, person_id, region, oenace, geschlecht, qualifikation, alter,
                                  %(note)s FROM ({select_sql}) x""", {**params, "copy_id": copy_id, "pid": pid, "oid": oid, "kind": kind,
                                                                       "note": note})
    return cur.rowcount


AGE_SWAP = ("CASE WHEN m.birth_date_raw ~ '^[0-9]{4}-13-(0[1-9]|1[0-2])$' THEN "
            "coalesce((SELECT k.code FROM klass_alter k WHERE k.version = '-' AND k.ebene = 'Altersjahr' AND k.code = "
            "extract(year FROM age((to_date(m.month, 'YYYY-MM') + interval '1 month - 1 day')::date, "
            "make_date(substr(m.birth_date_raw, 1, 4)::int, substr(m.birth_date_raw, 9, 2)::int, 13)))::int::text), 'UNB') ELSE 'UNB' END")
AGE_RAW = ("(extract(year FROM to_date(m.month, 'YYYY-MM')) - substr(m.birth_date_raw, 1, 4)::int)::text")


def apply(conn, copy_id: str, rule_set: str, months: list[str], filters: dict, choices: dict, free_text: dict, user: str | None,
          issues: list[dict]) -> dict:
    """Write the copy for the non-default choices; return what was done (removed/added per problem, hidden months, notes, SQL)."""
    conn.execute("DELETE FROM work.dq_copy WHERE copy_id = %s", (copy_id,))
    # SW-22: copies are working data – drop those older than COPY_DAYS (the choices in ops.dq_choice stay as the audit trail)
    conn.execute("DELETE FROM work.dq_copy WHERE created_at < now() - make_interval(days => %s)", (COPY_DAYS,))
    by_pid = {i["problem_id"]: i for i in issues}
    applied, hidden, notes, sqls = [], [], [], []
    for pid in list(dict.fromkeys(list(choices) + list(free_text))):
        issue = by_pid.get(pid)
        if not issue:
            continue
        oid = choices.get(pid) or issue["default"]
        interpreted = ""
        if free_text.get(pid):
            mapped, interpreted = interpret_free_text(conn, pid, free_text[pid], issue["options"])
            if mapped and not choices.get(pid):
                oid = mapped
            notes.append(f"{pid}: {interpreted}")
        opt = next((o for o in issue["options"] if o["id"] == oid), None)
        if not opt or not opt["available"]:
            notes.append(f"{pid}: Option {oid} hier nicht anwendbar – Standardbehandlung")
            opt = next(o for o in issue["options"] if o["is_default"])
        params = {"rule_set": rule_set, "months": months}
        where_f = _filter_sql(filters, params)
        base = (f"SELECT m.* FROM store.month_record m WHERE m.rule_set = %(rule_set)s AND m.month = ANY(%(months)s) "
                f"AND {AFFECTED.get(pid, 'false')}{where_f}")
        removed = added = 0
        a = opt["action"]
        # the official handling is already in the published values → nothing to copy; a non-official choice is applied,
        # also when its catalogue action is 'keep' (e.g. "Abschnitt C" while R-DQ07 would not be approved)
        if opt["is_default"]:
            a = "keep"
        elif a == "keep":
            a = {"DQ-07": "set_c", "DQ-08": "set_unknown", "DQ-02": "remove_carried", "DQ-04": "remove_carried",
                 "DQ-01": "swap_back", "DQ-16": "keep"}.get(pid, "keep")
        elif a == "age_unknown" and pid == "DQ-05" and official_option(conn, pid) == "unbekannt":
            a = "keep"
        if a == "swap_back":
            notes.append(f"{pid}: „{opt['label']}“ entspricht der freigegebenen Regel nicht – nicht umsetzbar, Standard bleibt")
            a = "keep"
        if a in ("set_c", "set_unknown"):
            removed = _insert_copy(conn, copy_id, pid, opt["id"], "removed", base, params)
            changed = ("SELECT m.month, m.vvh_id, m.person_id, m.region, 'C' AS oenace, m.geschlecht, m.qualifikation, m.alter FROM (" + base + ") m"
                       if a == "set_c" else
                       "SELECT m.month, m.vvh_id, m.person_id, CASE WHEN m.bundesland_raw IS NULL THEN '0' ELSE m.region END AS region, "
                       "CASE WHEN m.oenace_raw IS NULL THEN 'UNB' ELSE m.oenace END AS oenace, m.geschlecht, m.qualifikation, m.alter FROM (" + base + ") m")
            added = _insert_copy(conn, copy_id, pid, opt["id"], "added", changed, params)
            sqls.append(f"-- {pid} → {opt['label']}\n" + tools.render_sql(changed, params))
        elif a == "remove_carried":
            sel = (f"SELECT m.* FROM store.month_record m WHERE m.rule_set = %(rule_set)s AND m.month = %(m)s AND m.origin = 'carry_forward'"
                   f"{where_f}")
            params["m"] = MONTH_PROBLEMS[pid]
            removed = _insert_copy(conn, copy_id, pid, opt["id"], "removed", sel, params)
            sqls.append(f"-- {pid} → {opt['label']}\n" + tools.render_sql(sel, params))
        elif a == "keep":
            pass
        elif a == "hide_month":
            hidden.append(MONTH_PROBLEMS[pid])
        elif a in ("exclude", "age_unknown", "birth_swap", "age_raw", "oenace_unknown", "fill_from_earlier", "as_delivered"):
            if a == "as_delivered":
                base = (f"SELECT m.* FROM store.month_record m WHERE m.rule_set = %(rule_set)s AND m.month = '2025-06' "
                        f"AND '2025-06' = ANY(%(months)s){where_f}")
            removed = _insert_copy(conn, copy_id, pid, opt["id"], "removed", base, params)
            changed = {
                "age_unknown": "SELECT m.month, m.vvh_id, m.person_id, m.region, m.oenace, m.geschlecht, m.qualifikation, 'UNB' AS alter FROM (" + base + ") m",
                "birth_swap": f"SELECT m.month, m.vvh_id, m.person_id, m.region, m.oenace, m.geschlecht, m.qualifikation, {AGE_SWAP} AS alter FROM (" + base + ") m",
                "age_raw": f"SELECT m.month, m.vvh_id, m.person_id, m.region, m.oenace, m.geschlecht, m.qualifikation, {AGE_RAW} AS alter FROM (" + base + ") m",
                "oenace_unknown": "SELECT m.month, m.vvh_id, m.person_id, m.region, 'UNB' AS oenace, m.geschlecht, m.qualifikation, m.alter FROM (" + base + ") m",
                "fill_from_earlier": """SELECT m.month, m.vvh_id, m.person_id,
                       CASE WHEN m.bundesland_raw IS NULL THEN coalesce((SELECT e.bundesland FROM store.segment e WHERE e.vvh_id = m.vvh_id
                            AND e.delivery < m.month AND e.bundesland IS NOT NULL ORDER BY e.delivery DESC LIMIT 1), m.region) ELSE m.region END AS region,
                       CASE WHEN m.oenace_raw IS NULL THEN coalesce((SELECT e.oenace FROM store.segment e WHERE e.vvh_id = m.vvh_id
                            AND e.delivery < m.month AND e.oenace IS NOT NULL AND e.oenace !~ '^D[A-N]$'
                            AND (e.delivery >= '2025-01') = (m.month >= '2025-01') ORDER BY e.delivery DESC LIMIT 1), m.oenace) ELSE m.oenace END AS oenace,
                       m.geschlecht, m.qualifikation, m.alter FROM (""" + base + ") m",
                "as_delivered": """SELECT m.month, m.vvh_id, m.person_id, m.region, m.oenace, m.geschlecht, m.qualifikation, m.alter FROM (""" + base + """) m
                       WHERE EXISTS (SELECT 1 FROM store.segment s WHERE s.delivery = '2025-06' AND s.vvh_id = m.vvh_id
                                     AND store.iso_date(s.begin_raw) <= '2025-06-30'
                                     AND (s.end_raw IS NULL OR store.iso_date(s.end_raw) >= '2025-06-30'))""",
            }.get(a)
            if changed:
                added = _insert_copy(conn, copy_id, pid, opt["id"], "added", changed, params)
            if a == "fill_from_earlier":
                filled = conn.execute("""SELECT count(*) FROM work.dq_copy a JOIN work.dq_copy r ON r.copy_id = a.copy_id AND r.vvh_id = a.vvh_id
                                         AND r.month = a.month AND r.kind = 'removed' AND r.problem_id = a.problem_id
                                         WHERE a.copy_id = %s AND a.kind = 'added' AND a.problem_id = %s
                                         AND (a.region <> r.region OR a.oenace <> r.oenace)""", (copy_id, pid)).fetchone()[0]
                notes.append(f"{pid}: aus früheren Lieferungen ergänzt: {filled:,} von {removed:,} Verhältnissen".replace(",", ".")
                             + (" – die übrigen sind auch dort leer" if filled < removed else ""))
            sqls.append(f"-- {pid} → {opt['label']}\n" + tools.render_sql(changed or base, params))
        elif a == "exclude_confirmed":
            sel = base + " AND NOT EXISTS (SELECT 1 FROM store.segment n WHERE n.delivery = to_char(to_date(m.month, 'YYYY-MM') + interval '1 month', 'YYYY-MM') AND n.vvh_id = m.vvh_id) AND EXISTS (SELECT 1 FROM roh.ladeprotokoll l WHERE l.lieferung = to_char(to_date(m.month, 'YYYY-MM') + interval '1 month', 'YYYY-MM'))"
            removed = _insert_copy(conn, copy_id, pid, opt["id"], "removed", sel, params)
            sqls.append(f"-- {pid} → {opt['label']}\n" + tools.render_sql(sel, params))
        elif a == "carry_forward":
            m = MONTH_PROBLEMS[pid]
            fd = "AND p.qual_raw LIKE '%%FD'" if pid == "DQ-04" else ""
            params |= {"m": m, "p": tools._prev(m)}
            sel = (f"SELECT %(m)s AS month, p.vvh_id, p.person_id, p.region, p.oenace, p.geschlecht, p.qualifikation, p.alter FROM store.month_record p "
                   f"WHERE p.rule_set = %(rule_set)s AND p.month = %(p)s AND %(m)s = ANY(%(months)s) AND NOT ('DQ-16' = ANY(p.problems)) AND p.end_date IS NULL {fd}"
                   f"{_filter_sql(filters, params, 'p')} AND NOT EXISTS (SELECT 1 FROM store.segment c WHERE c.delivery = %(m)s AND c.vvh_id = p.vvh_id)")
            added = _insert_copy(conn, copy_id, pid, opt["id"], "added", sel, params, "Merkmale und Alter aus dem Vormonat")
            sqls.append(f"-- {pid} → {opt['label']}\n" + tools.render_sql(sel, params))
        applied.append({"problem_id": pid, "option_id": opt["id"], "label": opt["label"], "action": a, "removed": removed, "added": added,
                        "default": opt["is_default"]})
        conn.execute("""INSERT INTO ops.dq_choice ("user", copy_id, problem_id, option_id, free_text, interpreted, rows_removed, rows_added)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""", (user, copy_id, pid, opt["id"], free_text.get(pid), interpreted or None,
                                                                    removed, added))
    return {"copy_id": copy_id, "applied": applied, "hidden_months": hidden, "notes": notes, "sql": "\n\n".join(sqls)}


def adjust(conn, res: dict, handling: dict) -> dict:
    """Official result − removed + added from the copy, grouped like the question; hidden months dropped."""
    p = res["params"]
    dims = p["dimensions"]
    params = {"copy_id": handling["copy_id"]}
    where_f = tools._filter_sql(p["filters"], params)
    sel = "".join(f", {tools.DIMENSIONS[d][0]} AS {d}" for d in dims)
    group = "".join(f", {i + 2}" for i in range(len(dims)))
    delta_sql = (f"SELECT month AS monat{sel}, sum(CASE kind WHEN 'added' THEN 1 ELSE -1 END)::bigint AS delta\nFROM work.dq_copy\n"
                 f"WHERE copy_id = %(copy_id)s{where_f}\nGROUP BY 1{group}")
    deltas = {tuple(r[:-1]): int(r[-1]) for r in conn.execute(delta_sql, params).fetchall()}
    keyed = {tuple([r["monat"]] + [r[d] for d in dims]): dict(r) for r in res["rows"]}
    for key, d in deltas.items():
        if key not in keyed:
            row = {"monat": key[0], **{dim: key[i + 1] for i, dim in enumerate(dims)}, "wert": 0}
            names = {dim: tools.labels(conn, dim, p["months"]) for dim in dims}
            for i, dim in enumerate(dims):
                row[f"{dim}_label"] = names[dim].get(key[i + 1], key[i + 1])
            keyed[key] = row
        keyed[key]["offiziell"] = keyed[key].get("offiziell", keyed[key]["wert"])
        keyed[key]["wert"] = keyed[key]["wert"] + d
    rows = []
    for key in sorted(keyed, key=lambda k: tuple(str(x) for x in k)):
        r = keyed[key]
        if r["monat"] in handling["hidden_months"]:
            continue
        r.setdefault("offiziell", r["wert"])
        if r["wert"] or r["offiziell"]:
            rows.append(r)
    out = dict(res)
    out["rows"] = rows
    out["params"] = dict(p, months=[m for m in p["months"] if m not in handling["hidden_months"]])
    out["numbers"] = sorted({r["wert"] for r in rows} | {r["offiziell"] for r in rows})
    out["sql"] = (res["sql"] + "\n\n-- Behandlung auf der Kopie work.dq_copy (copy_id " + handling["copy_id"] + "):\n" +
                  tools.render_sql(delta_sql, params) + ("\n\n" + handling["sql"] if handling["sql"] else ""))
    return out


def copy_months(measure: str, months: list[str]) -> list[str]:
    """Months the copy must cover: flows compare with the previous month, so its records are treated too."""
    if measure in ("bestand", "personen"):
        return list(months)
    return sorted(set(months) | {tools._prev(m) for m in months})


def recompute(conn, res: dict, handling: dict) -> dict:
    """SW-07: Personen and Zu-/Abgänge/Fluktuation counted again on the treated record set
    (official month records − removed + added of the copy), with the same definitions as the official values
    (Personen = distinct PERSON_ID; Zugang = VVH in the month but not in the previous one, attributes of the month;
    Abgang = VVH in the previous month but not in the month, attributes of the previous month; rate = Abgänge ÷ previous stock)."""
    p = res["params"]
    measure, dims, months = p["measure"], p["dimensions"], p["months"]
    every = copy_months(measure, months)
    params = {"rule_set": p["rule_set"], "copy_id": handling["copy_id"], "every": every, "months": months}
    where_f = tools._filter_sql(p["filters"], params)
    sel = "".join(f", {tools.DIMENSIONS[d][0]} AS {d}" for d in dims)
    group = "".join(f", {i + 2}" for i in range(len(dims)))
    treated = """WITH t AS MATERIALIZED (
  SELECT m.month, m.vvh_id, m.person_id, m.region, m.oenace, m.geschlecht, m.qualifikation, m.alter
  FROM store.month_record m
  WHERE m.rule_set = %(rule_set)s AND m.month = ANY(%(every)s)
    AND NOT EXISTS (SELECT 1 FROM work.dq_copy r WHERE r.copy_id = %(copy_id)s AND r.kind = 'removed' AND r.month = m.month AND r.vvh_id = m.vvh_id)
  UNION ALL
  SELECT a.month, a.vvh_id, a.person_id, a.region, a.oenace, a.geschlecht, a.qualifikation, a.alter
  FROM work.dq_copy a WHERE a.copy_id = %(copy_id)s AND a.kind = 'added' AND a.month = ANY(%(every)s))"""
    if measure == "personen":
        sql = (f"{treated}\nSELECT month AS monat{sel}, count(DISTINCT person_id)::bigint AS wert\nFROM t\n"
               f"WHERE month = ANY(%(months)s){where_f}\nGROUP BY 1{group}\nORDER BY 1{group}")
    else:
        params["pairs"] = [f"{tools._prev(m)}>{m}" for m in months]
        keys = ["monat"] + dims
        k = ", ".join(keys)
        value = {"zugaenge": "coalesce(zu.n, 0)", "abgaenge": "coalesce(ab.n, 0)", "fluktuation": "coalesce(zu.n, 0) + coalesce(ab.n, 0)",
                 "fluktuationsrate": "round(100.0 * coalesce(ab.n, 0) / nullif(vb.n, 0), 2)"}[measure]
        sql = f"""{treated},
pairs AS (SELECT split_part(x, '>', 1) AS prev, split_part(x, '>', 2) AS cur FROM unnest(%(pairs)s::text[]) x),
zu AS (SELECT pr.cur AS monat{sel}, count(*) AS n FROM t JOIN pairs pr ON pr.cur = t.month
       WHERE NOT EXISTS (SELECT 1 FROM t o WHERE o.month = pr.prev AND o.vvh_id = t.vvh_id){where_f} GROUP BY 1{group}),
ab AS (SELECT pr.cur AS monat{sel}, count(*) AS n FROM t JOIN pairs pr ON pr.prev = t.month
       WHERE NOT EXISTS (SELECT 1 FROM t c WHERE c.month = pr.cur AND c.vvh_id = t.vvh_id){where_f} GROUP BY 1{group}),
vb AS (SELECT pr.cur AS monat{sel}, count(*) AS n FROM t JOIN pairs pr ON pr.prev = t.month WHERE true{where_f} GROUP BY 1{group}),
k AS (SELECT {k} FROM vb UNION SELECT {k} FROM zu UNION SELECT {k} FROM ab)
SELECT {', '.join('k.' + x for x in keys)}, {value} AS wert
FROM k LEFT JOIN vb USING ({k}) LEFT JOIN zu USING ({k}) LEFT JOIN ab USING ({k})
ORDER BY {', '.join(str(i + 1) for i in range(len(keys)))}"""
    with conn.transaction():
        conn.execute("SET LOCAL enable_nestloop = off")      # set operations on whole months: hash anti-joins
        conn.execute("SET LOCAL work_mem = '256MB'")
        cur = conn.execute(sql, params)
        cols = [c.name for c in cur.description]
        fresh = [dict(zip(cols, [float(v) if hasattr(v, "as_integer_ratio") and not isinstance(v, int) else v for v in r]))
                 for r in cur.fetchall()]
    official = {tuple([r["monat"]] + [r[d] for d in dims]): r for r in res["rows"]}
    names = {d: tools.labels(conn, d, months) for d in dims}
    rows = []
    for r in fresh:
        if r["monat"] in handling["hidden_months"]:
            continue
        key = tuple([r["monat"]] + [r[d] for d in dims])
        o = official.get(key)
        for d in dims:
            r[f"{d}_label"] = (o or {}).get(f"{d}_label") or names[d].get(r[d], r[d])
        r["offiziell"] = o["wert"] if o else 0
        rows.append(r)
    out = dict(res)
    out["rows"] = rows
    out["params"] = dict(p, months=[m for m in months if m not in handling["hidden_months"]])
    out["numbers"] = sorted({r["wert"] for r in rows if r["wert"] is not None} | {r["offiziell"] for r in rows if r["offiziell"] is not None})
    out["sql"] = (res["sql"] + "\n\n-- Neu gezählt auf der behandelten Kopie (offizielle Sätze − entfernt + hinzugefügt, copy_id "
                  + handling["copy_id"] + "):\n" + tools.render_sql(sql, params) + ("\n\n" + handling["sql"] if handling["sql"] else ""))
    return out
