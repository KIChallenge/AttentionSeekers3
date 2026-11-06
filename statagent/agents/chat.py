"""Fragen an die Daten – the medlyn-style chat that creates statistics (PRD §5.1, §5.3, F4).

Pipeline per question (events streamed to the UI):
  1. interpret: deterministic parser (statagent/agents/intent.py); with Azure configured the model may propose the
     parameters instead (function call) – they are validated like any other input, numbers never come from it
  2. ambiguity: a term of ops.term with always_ask (e.g. „Fluktuation“) → Rückfrage with the readings as options
  3. tool call: statagent/reporting/tools.py (SQL on stat_beschaeftigte / store.month_record / klass_*)
  4. card: KPIs, chart spec, table, SQL, definition, evidence – values copied from the result rows only
  5. text: German template filled from the result; claim check verifies every number before it is shown
  6. answer log: ops.answer (question, interpretation, tool calls, result hash, claim check, model, text)
Abstention is a first-class answer: „nicht vorhanden“, „nicht geliefert“, „mehrdeutig“, „nicht prüfbar“.
"""
import hashlib
import json
import re
import uuid

from statagent.agents import intent
from statagent.agents.llm import llm_status
from statagent.config import connect, connect_readonly
from statagent.reporting import claims, quality, tools
from statagent.reporting.explain import explain
from statagent.reporting.sources import sources_for

MONTH_NAMES = ["Jänner", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
DIM_LABEL = {"region": "Bundesland", "oenace": "Wirtschaftszweig", "geschlecht": "Geschlecht", "qualifikation": "Qualifikation",
             "kategorie": "Kategorie", "alter": "Alter", "altersgruppe": "Altersgruppe", "altersgruppe10": "Altersgruppe (10 Jahre)"}


def fmt(n, decimals: int = 0) -> str:
    if n is None:
        return "–"
    if decimals:
        return f"{n:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{int(round(n)):,}".replace(",", ".")


def month_label(m: str) -> str:
    y, mo = m.split("-")
    return f"{MONTH_NAMES[int(mo) - 1]} {y}"


def terms(conn, term: str) -> list[dict]:
    cur = conn.execute("""SELECT reading_id, label_de, definition_de, params, is_default FROM ops.term WHERE term = %s ORDER BY sort""", (term,))
    return [dict(id=r[0], label=r[1], definition=r[2], params=r[3], is_default=r[4]) for r in cur.fetchall()]


def suggestions(conn, role: str | None = None) -> list[dict]:
    rows = conn.execute("""SELECT text_de, role FROM ops.prompt_suggestion WHERE active AND (%s::text IS NULL OR role IN ('alle', %s))
                           ORDER BY sort""", (role, role)).fetchall()
    recent = conn.execute("""SELECT question FROM ops.answer WHERE kind = 'answer' GROUP BY question ORDER BY max(asked_at) DESC LIMIT 3""").fetchall()
    return [{"text_de": t, "role": r} for t, r in rows] + [{"text_de": q, "role": "zuletzt gefragt"} for (q,) in recent
                                                        if q not in {t for t, _ in rows}]


# --- cards -----------------------------------------------------------------------------------

def _pivot(rows: list[dict], dim: str) -> tuple[list[dict], list[dict]]:
    """Long rows (monat, dim, wert) → chart data per month with one key per code, and the series list."""
    codes, labels, by_month = [], {}, {}
    for r in rows:
        code = r[dim]
        if code not in labels:
            codes.append(code)
            labels[code] = r.get(f"{dim}_label") or code
        by_month.setdefault(r["monat"], {"monat": r["monat"]})[code] = r["wert"]
    return list(by_month.values()), [{"key": c, "label": f"{c} {labels[c]}" if dim == "oenace" else labels[c]} for c in codes]


def build_stat_card(conn, p: dict, res: dict) -> tuple[dict, str, list[float]]:
    """Card + German text + derived numbers (all derived deterministically from `res`)."""
    rows, months, dims = res["rows"], res["params"]["months"], res["params"]["dimensions"]
    unit = res["unit"]
    measure = res["params"]["measure"]
    dec = 2 if unit == "%" else 0
    derived: list[float] = []
    kpis, chart, text = [], None, []
    period = month_label(months[0]) if len(months) == 1 else f"{months[0]} bis {months[-1]}"
    what = tools.MEASURES[measure]
    title = f"{what} – {period}"
    if p.get("filters"):
        title += " · " + ", ".join(_filter_label(conn, k, v) for k, v in p["filters"].items())
    columns = [{"key": "monat", "label": "Monat"}] + [{"key": f"{d}_label", "label": DIM_LABEL[d]} for d in dims] + \
              [{"key": "wert", "label": "Wert" + (" (%)" if unit == "%" else "")}]
    table = {"columns": columns, "rows": rows}

    if not dims:
        values = [r["wert"] for r in rows]
        if len(months) == 1:
            v = values[0] if values else None
            kpis.append({"label": what, "value": v, "unit": unit})
            text.append(f"{month_label(months[0])}: **{fmt(v, dec)}**{' %' if unit == '%' else ''} {what if unit != '%' else ''}.".replace(" .", "."))
            prev = _previous_total(conn, p, months[0]) if measure in ("bestand", "personen") else None
            if prev is not None and v is not None:
                diff = v - prev
                derived += [prev, diff, round(100 * diff / prev, 1)]
                kpis[0]["delta"] = {"value": diff, "pct": round(100 * diff / prev, 1), "label": "zum Vormonat"}
                text.append(f"Gegenüber dem Vormonat ({fmt(prev)}) {'ein Plus' if diff >= 0 else 'ein Minus'} von {fmt(abs(diff))} "
                            f"({fmt(abs(100 * diff / prev), 1)} %).")
        else:
            first, last = values[0], values[-1]
            diff = last - first
            derived += [diff, round(100 * diff / first, 1) if first else 0, max(values), min(values)]
            kpis += [{"label": month_label(months[0]), "value": first, "unit": unit},
                     {"label": month_label(months[-1]), "value": last, "unit": unit,
                      "delta": {"value": diff, "pct": round(100 * diff / first, 1) if first else None, "label": f"seit {months[0]}"}}]
            hi = max(rows, key=lambda r: r["wert"]); lo = min(rows, key=lambda r: r["wert"])
            chart = {"kind": "line", "x": "monat", "series": [{"key": "wert", "label": what}], "data": rows}
            text.append(f"Von {month_label(months[0])} ({fmt(first, dec)}) bis {month_label(months[-1])} ({fmt(last, dec)}): "
                        f"{'+' if diff >= 0 else '−'}{fmt(abs(diff), dec)} ({fmt(abs(100 * diff / first), 1) if first else '–'} %). "
                        f"Höchster Wert {fmt(hi['wert'], dec)} ({hi['monat']}), niedrigster {fmt(lo['wert'], dec)} ({lo['monat']}).")
    elif len(dims) == 1:
        d = dims[0]
        if len(months) == 1:
            total = sum(r["wert"] for r in rows) if unit != "%" else None
            ordered = sorted(rows, key=lambda r: -r["wert"])
            if total is not None:
                derived.append(total)
                for r in rows:
                    derived.append(round(100 * r["wert"] / total, 1) if total else 0)
            if len(rows) <= 3:
                kpis += [{"label": r[f"{d}_label"], "value": r["wert"], "unit": unit,
                          "share": round(100 * r["wert"] / total, 1) if total else None} for r in rows]
                if total is not None:
                    kpis.append({"label": "Insgesamt", "value": total, "unit": unit})
            chart = {"kind": "bar", "x": f"{d}_label", "series": [{"key": "wert", "label": what}], "data": rows}
            parts = [f"{r[f'{d}_label']} {fmt(r['wert'], dec)}{' %' if unit == '%' else ''}"
                     + (f" ({fmt(100 * r['wert'] / total, 1)} %)" if total else "") for r in ordered[:6]]
            text.append(f"{month_label(months[0])} nach {DIM_LABEL[d]}: " + "; ".join(parts) + ("; …" if len(rows) > 6 else ".")
                        + (f" Insgesamt {fmt(total)}." if total is not None else ""))
        else:
            data, series = _pivot(rows, d)
            if measure in ("zugaenge", "abgaenge", "fluktuation", "fluktuationsrate") and d in ("oenace", "region", "qualifikation", "kategorie", "geschlecht"):
                agg = {}
                for r in rows:
                    e = agg.setdefault(r[d], {"code": r[d], "label": r.get(f"{d}_label"), "values": [], "missing": 0})
                    if r["wert"] is None:
                        e["missing"] += 1          # no stock in the previous month (e.g. new ÖNACE-2025 code in 01/2025)
                    else:
                        e["values"].append(r["wert"])
                summary = []
                for a in agg.values():
                    if not a["values"]:
                        continue
                    v = round(sum(a["values"]) / len(a["values"]), 2) if unit == "%" else sum(a["values"])
                    derived.append(v)
                    summary.append({d: a["code"], f"{d}_label": a["label"], "wert": v})
                summary.sort(key=lambda r: -r["wert"])
                how = "Durchschnitt der Monatsraten" if unit == "%" else "Summe über die Monate"
                chart = {"kind": "bar", "x": f"{d}_label", "series": [{"key": "wert", "label": f"{what} ({how})"}], "data": summary}
                table = {"columns": [{"key": f"{d}_label", "label": DIM_LABEL[d]}, {"key": "wert", "label": how}], "rows": summary,
                         "detail": rows}
                text.append(f"{what} {period} je {DIM_LABEL[d]} ({how}): " + "; ".join(
                    f"{r[f'{d}_label'] if d != 'oenace' else r[d]} {fmt(r['wert'], dec)}{' %' if unit == '%' else ''}" for r in summary[:5])
                    + ("; …" if len(summary) > 5 else "."))
            else:
                chart = {"kind": "line", "x": "monat", "series": series[:12], "data": data}
                firsts = {r[d]: r["wert"] for r in rows if r["monat"] == months[0]}
                lasts = {r[d]: r["wert"] for r in rows if r["monat"] == months[-1]}
                parts = []
                for s in series[:6]:
                    a, b = firsts.get(s["key"]), lasts.get(s["key"])
                    if a is not None and b is not None:
                        derived += [b - a, round(100 * (b - a) / a, 1) if a else 0]
                        parts.append(f"{s['label']} {fmt(a, dec)} → {fmt(b, dec)} ({'+' if b >= a else '−'}{fmt(abs(100 * (b - a) / a), 1) if a else '–'} %)")
                text.append(f"{DIM_LABEL[d]} von {months[0]} bis {months[-1]}: " + "; ".join(parts) + ("; …" if len(series) > 6 else ".") )
    else:
        d1, d2 = dims[0], dims[1]
        if len(months) == 1 and {d1, d2} & {"alter", "altersgruppe"} and "geschlecht" in (d1, d2):
            age = d1 if d1 != "geschlecht" else d2
            by_age = {}
            for r in rows:
                e = by_age.setdefault(r[age], {"alter": r.get(f"{age}_label") or r[age], "code": r[age], "M": 0, "W": 0})
                e[r["geschlecht"]] = e.get(r["geschlecht"], 0) + r["wert"]
            data = sorted(by_age.values(), key=lambda e: (e["code"] == "UNB", int(e["code"]) if str(e["code"]).isdigit() else 999,
                                                           str(e["code"])))
            chart = {"kind": "pyramid", "x": "alter", "series": [{"key": "M", "label": "Männer"}, {"key": "W", "label": "Frauen"}], "data": data}
            m_total, w_total = sum(e.get("M", 0) for e in data), sum(e.get("W", 0) for e in data)
            derived += [m_total, w_total, m_total + w_total]
            text.append(f"Altersverteilung {month_label(months[0])}: Männer {fmt(m_total)}, Frauen {fmt(w_total)}, insgesamt {fmt(m_total + w_total)}.")
        else:
            data, series = _pivot([{**r, "monat": r[f"{d1}_label"] if len(months) == 1 else r["monat"], d2: r[d2],
                                    f"{d2}_label": r.get(f"{d2}_label")} for r in rows], d2)
            chart = {"kind": "bar" if len(months) == 1 else "line", "x": "monat", "series": series[:12], "data": data, "stacked": len(months) == 1}
            text.append(f"{what} nach {DIM_LABEL[d1]} und {DIM_LABEL[d2]}, {period} – Werte siehe Tabelle.")
    card = {"title": title, "definition": res["definition"], "kpis": kpis, "chart": chart, "table": table, "sql": res["sql"],
            "evidence": res["evidence"], "warnings": res["warnings"], "params": res["params"], "unit": unit,
            "defaults": p.get("defaults", []), "notes": p.get("notes", [])}
    return card, " ".join(text), derived


def _previous_total(conn, p: dict, month: str):
    prev = tools._prev(month)
    try:
        r = tools.query_stat(conn, p["rule_set"], [prev], [], p.get("filters", {}), p["measure"])
    except tools.ToolError:
        return None
    return r["rows"][0]["wert"] if r["rows"] else None


def _filter_label(conn, key: str, values) -> str:
    names = tools.labels(conn, key, ["2026-07"]) if key in tools.LABEL_SQL or key == "oenace" else {}
    return ", ".join(names.get(v, v) for v in (values if isinstance(values, list) else [values]))


# --- metadata and QA answers ---------------------------------------------------------------------

def explain_card(conn, p: dict) -> tuple[dict, str, list[float]]:
    text_raw = explain(conn, p["klass"], p["code"], p.get("version"))
    table_name = {"region": "klass_region", "oenace": "klass_oenace"}[p["klass"]]
    rows = conn.execute("""SELECT u.version_alt, u.code_alt, u.version_neu, u.code_neu, u.beziehung, u.gueltig_ab, u.anteil, u.anmerkung,
                                  k.bezeichnung AS bezeichnung_neu
                           FROM klass_uebergang u LEFT JOIN """ + table_name + """ k ON k.version = u.version_neu AND k.code = u.code_neu
                           WHERE u.klassifikation = %s AND (u.code_alt = %s OR u.code_neu = %s)
                             AND (%s::text IS NULL OR u.version_alt = %s OR u.version_neu = %s)
                           ORDER BY u.gueltig_ab, u.anteil DESC NULLS LAST""",
                        (table_name, p["code"], p["code"], p.get("version"), p.get("version"), p.get("version"))).fetchall()
    cols = ["version_alt", "code_alt", "version_neu", "code_neu", "beziehung", "gueltig_ab", "anteil", "anmerkung", "bezeichnung_neu"]
    data = [dict(zip(cols, [x.isoformat() if hasattr(x, "isoformat") else (float(x) if x is not None and hasattr(x, "as_integer_ratio") else x)
                            for x in r])) for r in rows]
    shares = [d for d in data if d["anteil"] is not None and d["code_alt"] == p["code"]]
    derived = [round(100 * d["anteil"]) for d in shares] + [round(100 * d["anteil"], 1) for d in shares]
    chart = {"kind": "bar", "x": "code_neu", "series": [{"key": "anteil_pct", "label": "Anteil der Korrespondenzen (%)"}],
             "data": [{"code_neu": f"{d['code_neu']} {d['bezeichnung_neu'] or ''}".strip(), "anteil_pct": round(100 * d["anteil"], 1)}
                      for d in shares]} if shares else None
    sql = (f"SELECT * FROM klass_uebergang WHERE klassifikation = '{table_name}' AND (code_alt = '{p['code']}' OR code_neu = '{p['code']}')"
           + (f" AND (version_alt = '{p['version']}' OR version_neu = '{p['version']}')" if p.get("version") else "") + " ORDER BY gueltig_ab")
    card = {"title": f"Klassifikation: {table_name} {p['code']}" + (f" (Version {p['version']})" if p.get("version") else ""),
            "definition": "Deterministische Erklärung aus klass_*, klass_uebergang und quellzuordnung (python -m statagent erklaeren) – "
                          "der Text stammt nicht aus einem Sprachmodell.",
            "kpis": [], "chart": chart, "table": {"columns": [{"key": c, "label": c} for c in cols], "rows": data}, "sql": sql,
            "explanation": text_raw, "evidence": {"klass_run": tools.evidence(conn, "basis", [])["klass_run"]}, "warnings": [],
            "params": p, "kind": "explain", "graph": {"edges": data}}
    return card, "", derived


def quality_card(conn, p: dict, kind: str) -> tuple[dict, str, list[float]]:
    month = p["months"][0]
    run = conn.execute("""SELECT run_id, rules, checksum FROM ops.run WHERE kind = 'month' AND status = 'done' AND delivery = %s
                          AND rule_set = 'basis' AND note IS NULL ORDER BY run_id DESC LIMIT 1""", (month,)).fetchone()
    if not run:
        raise tools.ToolError(f"nicht vorhanden: für {month} gibt es noch keinen Lauf")
    run_id, rules, checksum = run
    findings = conn.execute("""SELECT problem_id, check_id, level, description, extent, classification, measure, rule_id, example_ids
                               FROM ops.finding WHERE run_id = %s ORDER BY finding_id""", (run_id,)).fetchall()
    rule_rows = conn.execute("""SELECT rule_id, title, status, approved_by, assumption FROM ops.rule
                                WHERE rule_id = ANY(%s) OR (status = 'proposed') ORDER BY rule_id""", (rules,)).fetchall()
    cls = {"explained_plausible": "erklärt – plausibel", "explained_data_problem": "erklärt – Datenproblem", "unexplained": "nicht erklärbar"}
    table_rows = [{"problem": f[0] or f[1], "ebene": f[2], "beschreibung": f[3], "umfang": f[4], "einstufung": cls.get(f[5], f[5]),
                   "massnahme": f[6], "beispiele": ", ".join(f[8] or [])} for f in findings]
    derived = [f[4] for f in findings if f[4] is not None] + [len(findings)]
    applied = [r for r in rule_rows if r[0] in (rules or [])]
    pending = [r for r in rule_rows if r[2] == "proposed"]
    text = (f"Lieferung {month} (Lauf {run_id}): {len(findings)} Auffälligkeiten. Angewendete Regeln: "
            + (", ".join(f"{r[0]} ({r[1]}, freigegeben von {r[3]})" for r in applied) or "keine")
            + ". Vorgeschlagen, noch nicht freigegeben: " + (", ".join(f"{r[0]}" for r in pending) or "keine") + ".")
    card = {"title": ("Qualitätsbericht " if kind == "quality" else "Annahmen und Auffälligkeiten – Lieferung ") + month,
            "definition": f"Aus ops.finding und ops.rule des Laufs {run_id} (Prüfsumme {checksum[:12]}…), Regelwerk Basis.",
            "kpis": [{"label": "Auffälligkeiten", "value": len(findings), "unit": "Anzahl"}], "chart": None,
            "table": {"columns": [{"key": k, "label": l} for k, l in (("problem", "Problem"), ("ebene", "Ebene"), ("beschreibung", "Beschreibung"),
                                                                      ("umfang", "Umfang"), ("einstufung", "Einstufung"), ("massnahme", "Maßnahme"),
                                                                      ("beispiele", "Beispiel-VVH"))], "rows": table_rows},
            "sql": f"SELECT * FROM ops.finding WHERE run_id = {run_id} ORDER BY finding_id", "evidence": tools.evidence(conn, "basis", [month]),
            "warnings": [], "params": p, "kind": kind, "link": f"/qualitaetsberichte/basis/{month}"}
    return card, text, derived


def definition_card(conn, p: dict) -> tuple[dict, str, list[float]]:
    var = conn.execute("SELECT variablenbezeichnung, beschreibung, einheit, berechnungslogik FROM variable WHERE statistik = 'beschaeftigte'").fetchall()
    desc = conn.execute("SELECT name, quelle, beschreibung, fussnoten FROM statistik_beschreibung WHERE statistik = 'beschaeftigte'").fetchone()
    text = f"{desc[0]}: {desc[2]} Quelle: {desc[1]}. {desc[3]}"
    card = {"title": "Definition – " + desc[0], "definition": "Aus den Metadaten-Tabellen variable und statistik_beschreibung (Anhang B).",
            "kpis": [], "chart": None, "table": {"columns": [{"key": k, "label": k} for k in ("variable", "beschreibung", "einheit", "berechnung")],
                                                 "rows": [dict(zip(("variable", "beschreibung", "einheit", "berechnung"), v)) for v in var]},
            "sql": "SELECT * FROM variable WHERE statistik = 'beschaeftigte'", "evidence": {}, "warnings": [], "params": p, "kind": "definition"}
    return card, text, []


# --- main entry --------------------------------------------------------------------------------

CHARTS = ["auto", "none", "bar", "hbar", "donut", "line", "area", "pyramid", "dot"]

AGENT_SYSTEM = """Du bist der Daten-Agent der österreichischen Beschäftigungsstatistik (StatAgent). Du beantwortest Fragen
ausschließlich, indem du GENAU EIN Werkzeug aufrufst. Du nennst NIE selbst Zahlen oder Fakten – die Werte kommen nur aus der
Datenbank (deterministisches SQL), der Text wird aus dem Ergebnis erzeugt.

Datenbestand (sonst nichts):
- Beschäftigungsverhältnisse aus 24 Monatslieferungen {first} bis {last} (Stichtag Monatsletzter; Regelwerk basis, nach den
  Änderungsaufträgen auch auftraege). Merkmale: Geschlecht (M/W), Bundesland des Arbeitsortes (Codes 1 Burgenland, 2 Kärnten,
  3 Niederösterreich, 4 Oberösterreich, 5 Salzburg, 6 Steiermark, 7 Tirol, 8 Vorarlberg, 9 Wien, 0 unbekannt), ÖNACE-Abschnitt
  (Buchstaben A–V; bis 12/2024 ÖNACE 2008, ab 01/2025 ÖNACE 2025), Qualifikation (ArbeiterDV, AngestellteDV, ArbeiterFD,
  AngestellteFD, Beamte), Alter / Altersgruppen. Kennzahlen: Verhältnisse (bestand), Personen, Zu-/Abgänge, Fluktuation(srate).
- Klassifikationen: Gemeinden/Bezirke 2011–2026 und ÖNACE 2003/2008/2025 mit Übergängen (Code erklären).
- Qualitätsberichte und Auffälligkeiten je Lieferung; Definitionen (Zählregeln).
- Pensionsstatistik 2018–2025 (Jahresdurchschnitt): Geschlecht, Pensionsart (ALTER, GEM, WIT, WAI; vorzeitige VAP, LVD, KOR,
  LZV, SA1, SA2), Versicherungsträger (PVA, SVS, BVAEB, SVA, SVB, VAEB, VAN; PV = alle, PV-UNS, PV-SELB).
NICHT geliefert: Einkommen, Dienstgeber, Wohnort, Arbeitszeit/Teilzeit, Arbeitslosigkeit, Staatsbürgerschaft, Bildung,
Gemeinde/Bezirk des Arbeitsortes.

Regeln:
1. Fragen ohne Bezug zu diesem Datenbestand (Geschichte, Physik, Allgemeinwissen, Smalltalk, Meinungen, Programmieren …)
   → decline_out_of_scope. Niemals selbst beantworten.
2. Fragen zu Merkmalen, die nicht geliefert wurden → report_not_in_data mit dem fehlenden Merkmal.
3. Sonst das passende Werkzeug mit Parametern. Monate als JJJJ-MM; „Juni 2026“ = 2026-06; ein Jahr = alle Monate des Jahres
   im Datenbestand; ohne Zeitangabe keine Monate (dann gilt der letzte Monat). Männer und Frauen → Gliederung geschlecht.
   Standardkennzahl ist bestand (Beschäftigungsverhältnisse, amtliche Zählung) – auch bei „Beschäftigte“, „Leute“, „people“,
   „worked“; personen nur, wenn ausdrücklich Personen/Köpfe (jede Person einmal) gemeint sind.
4. chart: wähle die Darstellung, die die Aussage am klarsten zeigt: Zeitverlauf (Monate/Jahre) → line; Anteile an einem Ganzen
   mit 2–6 Gruppen (z. B. Männer/Frauen, Pensionsarten) → donut; Vergleich vieler Gruppen oder lange Namen (Bundesländer,
   ÖNACE) → hbar; geordnete Gruppen (Altersgruppen) → bar; Alter nach Geschlecht → pyramid; eine einzelne Zahl → none.
   Liegen die Werte nahe beieinander (z. B. Raten je Bundesland, leichte Schwankungen über Monate), keine Balken ab 0, sondern
   dot (Punkte auf gezoomter Achse) bzw. line – die Darstellung zoomt dann automatisch auf den Wertebereich.
5. Die Frage darf englisch sein; die Parameter bleiben wie beschrieben.
Vorherige Abfrage (für Folgefragen wie „und nur Frauen?“): {previous}"""


def _agent_tools() -> list[dict]:
    def fn(name, desc, props, required=()):
        return {"type": "function", "function": {"name": name, "description": desc,
                                                 "parameters": {"type": "object", "properties": props, "required": list(required)}}}
    chart = {"type": "string", "enum": CHARTS, "description": "gewünschte Darstellung"}
    filters = {"type": "object", "additionalProperties": {"type": "array", "items": {"type": "string"}},
               "description": "Spalte → Codes, z. B. {\"region\": [\"9\"], \"geschlecht\": [\"W\"]}"}
    return [
        fn("query_employment", "Beschäftigungsstatistik abfragen (Verhältnisse, Personen, Zu-/Abgänge, Fluktuation).",
           {"measure": {"type": "string", "enum": list(tools.MEASURES) + ["ambiguous_fluktuation"]},
            "months": {"type": "array", "items": {"type": "string", "pattern": "^20\\d{2}-\\d{2}$"}},
            "dimensions": {"type": "array", "items": {"type": "string", "enum": list(tools.DIMENSIONS)}},
            "filters": filters, "rule_set": {"type": "string", "enum": list(tools.RULE_SETS)}, "chart": chart}, ["measure"]),
        fn("query_pensions", "Pensionsstatistik (Jahresdurchschnitt 2018–2025) abfragen.",
           {"years": {"type": "array", "items": {"type": "integer", "minimum": 2018, "maximum": 2025}},
            "dimensions": {"type": "array", "items": {"type": "string", "enum": list(tools.PENSION_DIMS)}},
            "filters": filters, "chart": chart}),
        fn("explain_code", "Einen Gemeinde-/Bezirks- oder ÖNACE-Code erklären (Bedeutung, Änderungen, Übergänge).",
           {"klass": {"type": "string", "enum": ["region", "oenace"]}, "code": {"type": "string"},
            "version": {"type": "string", "enum": ["2003", "2008", "2025"]}}, ["klass", "code"]),
        fn("quality_report", "Qualitätsbericht bzw. Annahmen/Auffälligkeiten einer Lieferung.",
           {"month": {"type": "string", "pattern": "^20\\d{2}-\\d{2}$"}, "kind": {"type": "string", "enum": ["quality", "assumptions"]}}),
        fn("definition", "Definition und Zählregeln der Beschäftigtenstatistik.", {}),
        fn("report_not_in_data", "Das gefragte Merkmal ist in den Lieferungen nicht enthalten.",
           {"missing": {"type": "string", "description": "fehlendes Merkmal, deutsch"}}, ["missing"]),
        fn("decline_out_of_scope", "Die Frage hat keinen Bezug zum Datenbestand und wird nicht beantwortet.",
           {"topic": {"type": "string", "description": "Thema der Frage in wenigen Wörtern, deutsch"}}, ["topic"]),
    ]


def llm_parse(question: str, available: list[str], previous: dict | None) -> dict | None:
    """Agent step: with a model configured (AGENT_* in .env) the model picks ONE tool and its parameters by function calling –
    or declines. Parameters are validated by the tools like any other input; numbers never come from the model.
    None = no model or call failed → the deterministic parser answers."""
    if not llm_status()["configured"]:
        return None
    from statagent.agents.llm import LLMUnavailable, chat
    prev = {k: (previous or {}).get(k) for k in ("kind", "measure", "months", "dimensions", "filters", "rule_set", "years")} if previous else {}
    system = AGENT_SYSTEM.format(first=available[0], last=available[-1], previous=json.dumps(prev, ensure_ascii=False)[:1500])
    try:
        r = chat([{"role": "system", "content": system}, {"role": "user", "content": question}], tools=_agent_tools(),
                 purpose="chat:agent", tool_choice="required")
    except LLMUnavailable:
        return None
    if not r["tool_calls"]:
        return None
    call = r["tool_calls"][0]
    name, a = call["name"], call["arguments"] or {}
    parsed = intent.parse(question, available)           # defaults/notes stay deterministic
    det_kind = parsed["kind"]
    parsed.update(model=r["model"], agent_tool=name, agent_arguments=a, chart_pref=a.get("chart"))
    if det_kind == "unavailable":                          # documented missing fields always win (deterministic list)
        return parsed
    if name == "decline_out_of_scope":
        parsed.update(kind="out_of_scope", topic=a.get("topic"))
    elif name == "report_not_in_data":
        parsed.update(kind="unavailable", missing=a.get("missing") or "dieses Merkmal")
    elif name == "query_pensions":
        parsed.update(kind="pension", years=a.get("years") or [], dimensions=a.get("dimensions") or [], filters=a.get("filters") or {},
                      months=[str(y) for y in a.get("years") or []])
    elif name == "explain_code":
        parsed.update(kind="explain", klass=a.get("klass"), code=str(a.get("code", "")).upper() if a.get("klass") == "oenace" else a.get("code"),
                      version=a.get("version"))
    elif name == "quality_report":
        parsed.update(kind=a.get("kind") or "quality", months=[a["month"]] if a.get("month") else available[-1:])
    elif name == "definition":
        parsed["kind"] = "definition"
    else:
        parsed["kind"] = "stat"
        if a.get("months"):
            parsed["months"] = a["months"]
            parsed["defaults"] = [d for d in parsed["defaults"] if not d.startswith("kein Zeitraum")]
        for k in ("dimensions", "filters", "rule_set"):
            if a.get(k) is not None:
                parsed[k] = a[k]
        if a.get("measure") == "ambiguous_fluktuation":
            parsed["ambiguous"] = ["fluktuation"]
        elif a.get("measure"):
            parsed["measure"], parsed["ambiguous"] = a["measure"], []
        # safety net: the deterministic check found no link to the data and the model named nothing specific
        if det_kind == "out_of_scope" and not (a.get("months") or a.get("dimensions") or a.get("filters")):
            parsed["kind"] = "out_of_scope"
    return parsed


def pension_card(conn, p: dict, res: dict) -> tuple[dict, str, list[float]]:
    """Pension statistic card – values only from the result rows."""
    rows, dims, years = res["rows"], res["params"]["dimensions"], res["params"]["years"]
    labels = {"geschlecht": "Geschlecht", "pensionsart": "Pensionsart", "versicherungstraeger": "Versicherungsträger"}
    period = str(years[0]) if len(years) == 1 else f"{years[0]} bis {years[-1]}"
    title = f"Pensionen (Jahresdurchschnitt) – {period}"
    kpis, chart, text, derived = [], None, [], []
    if not dims:
        if len(years) == 1:
            v = rows[0]["wert"] if rows else None
            kpis.append({"label": "Pensionen", "value": v, "unit": "Anzahl"})
            text.append(f"{period}: **{fmt(v)}** Pensionen im Jahresdurchschnitt.")
        else:
            first, last = rows[0]["wert"], rows[-1]["wert"]
            derived += [last - first, round(100 * (last - first) / first, 1) if first else 0]
            kpis += [{"label": str(years[0]), "value": first, "unit": "Anzahl"},
                     {"label": str(years[-1]), "value": last, "unit": "Anzahl",
                      "delta": {"value": last - first, "pct": round(100 * (last - first) / first, 1) if first else None, "label": f"seit {years[0]}"}}]
            chart = {"kind": "line", "x": "monat", "series": [{"key": "wert", "label": "Pensionen"}], "data": rows}
            text.append(f"Von {years[0]} ({fmt(first)}) bis {years[-1]} ({fmt(last)}): {'+' if last >= first else '−'}{fmt(abs(last - first))}.")
    elif len(dims) == 1 and len(years) == 1:
        d = dims[0]
        total = sum(r["wert"] for r in rows)
        derived.append(total)
        derived += [round(100 * r["wert"] / total, 1) if total else 0 for r in rows]
        if len(rows) <= 3:
            kpis += [{"label": r[f"{d}_label"], "value": r["wert"], "unit": "Anzahl", "share": round(100 * r["wert"] / total, 1) if total else None}
                     for r in rows] + [{"label": "Insgesamt", "value": total, "unit": "Anzahl"}]
        chart = {"kind": "bar", "x": f"{d}_label", "series": [{"key": "wert", "label": "Pensionen"}], "data": rows}
        text.append(f"{period} nach {labels[d]}: " + "; ".join(f"{r[f'{d}_label']} {fmt(r['wert'])} ({fmt(100 * r['wert'] / total, 1)} %)"
                                                            for r in sorted(rows, key=lambda r: -r["wert"])[:6]) + f". Insgesamt {fmt(total)}.")
    elif len(dims) == 1:
        data, series = _pivot(rows, dims[0])
        chart = {"kind": "line", "x": "monat", "series": series[:12], "data": data}
        text.append(f"Pensionen nach {labels[dims[0]]}, {period} – Werte siehe Tabelle.")
    else:
        text.append(f"Pensionen nach {' und '.join(labels[d] for d in dims)}, {period} – Werte siehe Tabelle.")
    cols = [{"key": "jahr", "label": "Jahr"}] + [{"key": f"{d}_label", "label": labels[d]} for d in dims] + [{"key": "wert", "label": "Pensionen"}]
    card = {"title": title, "definition": res["definition"], "kpis": kpis, "chart": chart, "table": {"columns": cols, "rows": rows},
            "sql": res["sql"], "evidence": res["evidence"], "warnings": res["warnings"], "params": res["params"], "unit": "Anzahl",
            "defaults": p.get("defaults", []), "notes": p.get("notes", []), "kind": "pension"}
    return card, " ".join(text), derived


def apply_chart(card: dict, pref: str | None) -> None:
    """The agent's chart wish, applied only where the data fit it (values stay the same, only the form changes)."""
    ch = card.get("chart")
    if not pref or pref == "auto":
        return
    if pref == "none":
        card["chart"] = None
        return
    if not ch or not ch.get("data"):
        return
    single_series = len(ch.get("series", [])) == 1
    by_time = ch.get("x") == "monat" and len(ch["data"]) > 1 and not ch.get("stacked")
    if pref in ("line", "area") and by_time:
        ch["kind"] = pref
    elif pref in ("bar", "hbar") and ch["kind"] != "pyramid":
        ch["kind"] = pref
    elif pref == "donut" and single_series and not by_time and len(ch["data"]) <= 8 and card.get("unit") != "%":
        ch["kind"] = "donut"
    elif pref == "pyramid" and ch["kind"] == "pyramid":
        pass
    elif pref == "dot" and single_series and not by_time:
        ch["kind"] = "dot"


TERM_ORDER = ("fluktuation", "personen", "kategorie", "jahr", "entwicklung", "alter", "oenace_bruch", "monat")
DV = {"Arbeiter": ["ArbeiterDV"], "Angestellte": ["AngestellteDV"]}
WITH_FD = {"Arbeiter": ["ArbeiterDV", "ArbeiterFD"], "Angestellte": ["AngestellteDV", "AngestellteFD"]}


def term_catalogue(conn) -> dict[str, dict]:
    """ops.term → {term: {trigger, resolve, ask_when, question, options}} (rules as data, extendable by the Fachabteilung)."""
    out: dict[str, dict] = {}
    for term, rid, label, definition, params, default, trig, res, when, question in conn.execute(
            """SELECT term, reading_id, label_de, definition_de, params, is_default, trigger_regex, resolve_regex, ask_when, question_de
               FROM ops.term ORDER BY term, sort"""):
        t = out.setdefault(term, {"term": term, "trigger": None, "resolve": None, "ask_when": when, "question": None, "options": []})
        t["trigger"] = t["trigger"] or trig
        t["resolve"] = t["resolve"] or res
        t["question"] = t["question"] or question
        t["options"].append({"id": rid, "label": label, "definition": definition, "params": params, "is_default": default})
    return out


def next_ambiguity(conn, ro, question: str, p: dict, readings: dict, available: list[str]) -> dict | None:
    """First term of the catalogue that occurs in the question, is not resolved by it, applies to this request and was not
    answered yet. Returns the clarification (question + options) or None."""
    if p.get("kind") != "stat":
        return None
    q = intent.norm(question)
    cat = term_catalogue(conn)
    for name in list(TERM_ORDER) + sorted(set(cat) - set(TERM_ORDER)):
        t = cat.get(name)
        if not t or not t["trigger"] or name in readings:
            continue
        m = re.search(t["trigger"], q)
        if not m or (t["resolve"] and re.search(t["resolve"], q)):
            continue
        months, when = p.get("months", []), t["ask_when"]
        if when == "single_month" and not (len(months) == 1 and p["measure"] == "bestand"):
            continue
        if when == "year_only" and not (p["measure"] == "bestand" and len(months) > 1 and len({x[:4] for x in months}) == 1
                                        and not re.search(r"\b(0?[1-9]|1[0-2])/20\d{2}\b|20\d{2}-\d{2}", q)):
            continue
        if when == "oenace_break" and not (("oenace" in p.get("dimensions", []) or "oenace" in p.get("filters", {}))
                                           and any(x <= "2024-12" for x in months) and any(x >= "2025-01" for x in months)):
            continue
        if when == "both_rule_sets" and not ro.execute("SELECT 1 FROM stat_beschaeftigte WHERE regelwerk = 'auftraege' LIMIT 1").fetchone():
            continue
        if name == "kategorie" and not re.search(r"\b(arbeiter|angestellte[n]?)\b", q):
            continue
        return {"term": name, "word": m.group(0), "question": (t["question"] or f"„{m.group(0)}“ ist mehrdeutig – welche Lesart?").replace("{wort}", m.group(0)),
                "options": [{k: o[k] for k in ("id", "label", "definition", "is_default")} for o in t["options"]]}
    return None


def apply_reading(conn, question: str, p: dict, term: str, choice: str, available: list[str]) -> str | None:
    """Apply a chosen reading to the parameters. Returns an abstention reason if the reading cannot be answered."""
    cat = term_catalogue(conn)
    opt = next((o for o in cat.get(term, {}).get("options", []) if o["id"] == choice), None)
    if not opt:
        return None
    prm = opt["params"] or {}
    if prm.get("unavailable"):
        return f"nicht vorhanden: {opt['label']} – {opt['definition']}"
    q = intent.norm(question)
    months = list(p.get("months") or available[-1:])
    if "measure" in prm and prm["measure"]:
        p["measure"] = prm["measure"]
        p["ambiguous"] = []
    if "rule_set" in prm:
        p["rule_set"] = prm["rule_set"]
    if prm.get("compare"):
        m = months[-1]
        if prm["compare"] == "prev":
            p["months"] = [x for x in (tools._prev(m), m) if x in available]
        elif prm["compare"] == "year":
            y = f"{int(m[:4]) - 1}{m[4:]}"
            if y not in available:
                return f"nicht vorhanden: Der Vorjahresmonat {y} liegt vor Beginn des Datenbestands ({available[0]})."
            p["months"] = [y, m]
        else:
            p["months"] = [x for x in available if x <= m]
    if prm.get("year"):
        if prm["year"] == "mean":
            p["aggregate"] = "mean"
        elif prm["year"] == "last":
            p["months"] = months[-1:]
    if prm.get("kategorie"):
        named = [c for c in ("Arbeiter", "Angestellte") if re.search(rf"\b{c.lower()}", q)]
        dims = [d for d in p.get("dimensions", []) if d not in ("qualifikation", "kategorie")]
        if prm["kategorie"] == "getrennt":
            p["dimensions"] = dims + ["qualifikation"]
            if len(named) == 1:
                p.setdefault("filters", {})["qualifikation"] = WITH_FD[named[0]]
        else:
            codes = WITH_FD if prm["kategorie"] == "mit_fd" else DV
            if len(named) == 1:
                p.setdefault("filters", {})["qualifikation"] = codes[named[0]]
                p["dimensions"] = dims
            else:
                p["dimensions"] = dims + ["kategorie"]
                if prm["kategorie"] == "nur_dv":
                    p.setdefault("filters", {})["qualifikation"] = ["ArbeiterDV", "AngestellteDV", "Beamte"]
        p["defaults"] = [d for d in p.get("defaults", []) if not d.startswith("Arbeiter/Angestellte")]
    if prm.get("oenace_period"):
        if prm["oenace_period"] == "2025":
            p["months"] = [x for x in months if x >= "2025-01"]
        elif prm["oenace_period"] == "2008":
            p["months"] = [x for x in months if x <= "2024-12"]
        if not p["months"]:
            return "nicht vorhanden: Im gewählten Zeitraum gibt es keine Monate dieser ÖNACE-Version."
    if prm.get("age"):
        p["dimensions"] = [prm["age"] if d in ("alter", "altersgruppe", "altersgruppe10") else d for d in p.get("dimensions", [])]
        if prm["age"] not in p["dimensions"]:
            p["dimensions"].append(prm["age"])
    p.setdefault("defaults", []).insert(0, f"gewählte Lesart: {opt['label']} – {opt['definition']}")
    if prm.get("note"):
        p.setdefault("notes", []).append(prm["note"])
    return None


def mean_card(conn, p: dict, res: dict) -> tuple[dict, str, list[float]]:
    """Jahresdurchschnitt: mean of the monthly values per group (deterministic, rounded to whole relationships)."""
    dims, months = res["params"]["dimensions"], res["params"]["months"]
    groups: dict = {}
    for r in res["rows"]:
        key = tuple(r[d] for d in dims)
        g = groups.setdefault(key, {**{d: r[d] for d in dims}, **{f"{d}_label": r.get(f"{d}_label") for d in dims}, "werte": []})
        g["werte"].append(r["wert"])
    rows, derived = [], []
    for g in groups.values():
        v = round(sum(g["werte"]) / len(g["werte"]))
        derived += [v, len(g["werte"])]
        rows.append({**{k: x for k, x in g.items() if k != "werte"}, "wert": v, "monate": len(g["werte"])})
    year = months[0][:4]
    label = "Jahresdurchschnitt " + year + (f" ({months[0]} bis {months[-1]}, {len(months)} Monate)" if len(months) < 12 else "")
    kpis = [{"label": (r.get(f"{dims[0]}_label") if dims else "Insgesamt") or "Insgesamt", "value": r["wert"], "unit": "Anzahl"}
            for r in rows[:3]] if len(rows) <= 3 else []
    chart = {"kind": "bar", "x": f"{dims[0]}_label", "series": [{"key": "wert", "label": label}], "data": rows} if dims else None
    cols = [{"key": f"{d}_label", "label": DIM_LABEL[d]} for d in dims] + [{"key": "wert", "label": label}, {"key": "monate", "label": "Monate"}]
    text = (f"{label}: " + "; ".join(f"{(r.get(f'{dims[0]}_label') if dims else 'insgesamt')} {fmt(r['wert'])}" for r in rows[:6])
            + ("; …" if len(rows) > 6 else ".") + " Gerundet auf ganze Verhältnisse.")
    card = {"title": f"{tools.MEASURES[res['params']['measure']]} – {label}", "definition": res["definition"] + " · Mittelwert der Monatsstände",
            "kpis": kpis, "chart": chart, "table": {"columns": cols, "rows": rows, "detail": res["rows"]}, "sql": res["sql"],
            "evidence": res["evidence"], "warnings": res["warnings"], "params": res["params"] | {"aggregate": "mean"}, "unit": "Anzahl",
            "defaults": p.get("defaults", []), "notes": p.get("notes", [])}
    return card, text, derived


def answer(question: str, user: str | None = None, role: str | None = None, conversation: str | None = None,
           previous: dict | None = None, reading: dict | None = None, emit=lambda kind, data: None,
           handling: dict | None = None, free_text: dict | None = None) -> dict:
    question = (question or "").strip()[:1000]
    handling, free_text = dict(handling or {}), {k: str(v)[:500] for k, v in (free_text or {}).items() if v}
    with connect() as conn, connect_readonly(autocommit=True) as ro:   # all tool SQL runs read-only (PRD §5.1)
        available = [r[0] for r in conn.execute("SELECT DISTINCT substr(stand, 11) FROM stat_beschaeftigte WHERE regelwerk = 'basis' ORDER BY 1")]
        if not available:
            emit("abstention", {"kind": "nicht vorhanden", "reason": "Es gibt noch keine Ergebnisse – zuerst die Monatsläufe starten."})
            return {"kind": "abstention"}
        emit("status", {"text": "Frage wird gelesen …"})
        p = llm_parse(question, available, previous) or intent.parse(question, available)
        p = intent.merge_follow_up(p, previous, question)
        p["ambiguous"] = []                    # ambiguity is decided by the term catalogue below (ops.term)
        model = p.get("model") or llm_status()["mode_label"]
        if p.get("agent_tool"):
            emit("status", {"text": f"Agent ({model}) hat das Werkzeug „{p['agent_tool']}“ gewählt …",
                            "agent": {"tool": p["agent_tool"], "arguments": p.get("agent_arguments")}})
        emit("status", {"text": "Prüfe, ob die Information im Datenbestand vorhanden ist …"})
        if p["kind"] == "out_of_scope":
            reason = intent.OUT_OF_SCOPE_TEXT + (f" (Thema: {p['topic']})" if p.get("topic") else "")
            emit("abstention", {"kind": "außerhalb des Datenbestands", "reason": reason})
            _log(conn, user, role, conversation, question, p, None, None, None, model, reason, "abstention")
            return {"kind": "abstention"}
        readings = dict(reading or {})
        for term, choice in readings.items():
            reason = apply_reading(conn, question, p, term, choice, available)
            if reason:
                emit("abstention", {"kind": "nicht vorhanden", "reason": reason})
                _log(conn, user, role, conversation, question, p, None, None, None, model, reason, "abstention")
                return {"kind": "abstention"}
        clar = next_ambiguity(conn, ro, question, p, readings, available)
        if clar:
            emit("clarification", {**clar, "answered": readings,
                                   "pending": {k: p.get(k) for k in ("months", "dimensions", "filters", "rule_set", "measure")}})
            _log(conn, user, role, conversation, question, p, None, None, None, model, None, "clarification")
            return {"kind": "clarification", "params": p}
        emit("status", {"text": "Abfrage wird ausgeführt …", "interpretation": {k: p.get(k) for k in ("kind", "measure", "months", "dimensions", "filters", "rule_set")}})
        quality_info = None
        try:
            if p["kind"] == "explain":
                card, text, derived = explain_card(ro, p)
                result_numbers = []
            elif p["kind"] in ("quality", "assumptions"):
                card, text, derived = quality_card(ro, p, p["kind"])
                result_numbers = []
            elif p["kind"] == "definition":
                card, text, derived = definition_card(ro, p)
                result_numbers = []
            elif p["kind"] == "pension":
                res = tools.query_pension(ro, p.get("years") or None, p.get("dimensions"), p.get("filters"))
                if not res["rows"]:
                    reason = "nicht vorhanden: Für diese Merkmale enthält die Pensionsstatistik keine Werte."
                    emit("abstention", {"kind": "nicht vorhanden", "reason": reason, "sql": res["sql"]})
                    _log(conn, user, role, conversation, question, p, [res["params"]], None, None, model, reason, "abstention")
                    return {"kind": "abstention"}
                p["years"], p["months"] = res["params"]["years"], [str(y) for y in res["params"]["years"]]
                card, text, derived = pension_card(ro, p, res)
                derived = list(derived) + list(res["params"]["years"])      # years may appear in the text
                result_numbers = res["numbers"]
            elif p["kind"] == "unavailable":
                reason = f"{p['missing']} ist in den Lieferungen nicht enthalten. {intent.AVAILABLE_TEXT}"
                emit("abstention", {"kind": "nicht verfügbar", "reason": reason, "missing": p["missing"]})
                _log(conn, user, role, conversation, question, p, None, None, None, model, reason, "abstention")
                return {"kind": "abstention"}
            elif p["kind"] == "unknown":
                reason = ("mehrdeutig – bitte präzisieren: Die Frage lässt sich keiner Statistik zuordnen. Beispiele: "
                          "„Männer und Frauen im Juli 2026“, „Zeitreihe der Beschäftigten“, „Erkläre Gemeinde 62388“.")
                emit("abstention", {"kind": "mehrdeutig", "reason": reason})
                _log(conn, user, role, conversation, question, p, None, None, None, model, reason, "abstention")
                return {"kind": "abstention"}
            else:
                res = tools.query_stat(ro, p["rule_set"], p["months"], p["dimensions"], p["filters"], p["measure"])
                if not res["rows"]:
                    reason = "nicht vorhanden: Die Abfrage lief, liefert für diese Merkmale aber keine Fälle (0 Verhältnisse)."
                    emit("abstention", {"kind": "nicht vorhanden", "reason": reason, "sql": res["sql"]})
                    _log(conn, user, role, conversation, question, p, [res["params"]], None, None, model, reason, "abstention")
                    return {"kind": "abstention"}
                if p["measure"] in ("zugaenge", "abgaenge", "fluktuation", "fluktuationsrate") and "oenace" in p["dimensions"] and "2025-01" in p["months"]:
                    res["warnings"].append("01/2025: Abgänge nach ÖNACE 2008 (Merkmale des Vormonats), Zugänge nach ÖNACE 2025 – Klassifikationsbruch.")
                emit("status", {"text": "Datenqualität der benötigten Felder wird geprüft …"})
                issues = quality.detect(ro, p["rule_set"], res["params"]["months"], p["dimensions"], p["filters"], p["measure"])
                applied = None
                if handling or free_text:
                    copy_id = "A" + uuid.uuid4().hex[:12]
                    with conn.transaction():
                        applied = quality.apply(conn, copy_id, p["rule_set"], quality.copy_months(p["measure"], res["params"]["months"]),
                                                p["filters"], handling, free_text, user, issues)
                    if any(not a["default"] for a in applied["applied"]) or applied["hidden_months"]:
                        # Verhältnisse: official − removed + added; Personen and Zu-/Abgänge: recounted on the treated copy (SW-07)
                        res = quality.adjust(conn, res, applied) if p["measure"] == "bestand" else quality.recompute(conn, res, applied)
                        if not res["rows"]:
                            emit("abstention", {"kind": "nicht vorhanden", "reason": "Mit der gewählten Behandlung bleibt kein Monat übrig."})
                            return {"kind": "abstention"}
                        res["warnings"].insert(0, "Eigene Behandlung fehlerhafter Daten auf einer Kopie der betroffenen Sätze – "
                                                  "keine amtliche Zahl; die veröffentlichten Werte bleiben unverändert (Spalte „offiziell“).")
                        res["definition"] += " · Behandlung: " + "; ".join(f"{a['problem_id']} {a['label']}" for a in applied["applied"]
                                                                             if not a["default"]) + \
                            ("; ausgeblendet: " + ", ".join(applied["hidden_months"]) if applied["hidden_months"] else "")
                chosen = {a["problem_id"]: a["option_id"] for a in (applied or {}).get("applied", [])}
                for i in issues:
                    i["chosen"] = chosen.get(i["problem_id"], i["default"])
                    i["free_text"] = free_text.get(i["problem_id"], "")
                quality_info = {"issues": issues, "handling": applied}
                if p.get("aggregate") == "mean":
                    card, text, derived = mean_card(ro, p, res)
                else:
                    card, text, derived = build_stat_card(conn, p, res)
                if applied and any("offiziell" in r for r in card["table"]["rows"]):
                    card["table"]["columns"].append({"key": "offiziell", "label": "offiziell (freigegebene Regeln)"})
                result_numbers = res["numbers"]
        except tools.ToolError as exc:
            msg = str(exc)
            kind = "nicht vorhanden" if msg.startswith("nicht vorhanden") else "nicht prüfbar"
            emit("abstention", {"kind": kind, "reason": msg})
            _log(conn, user, role, conversation, question, p, None, None, None, model, msg, "abstention")
            return {"kind": "abstention"}
        if quality_info:
            card["quality"] = quality_info
        card["readings"] = readings
        apply_chart(card, p.get("chart_pref"))
        card["sources"] = sources_for(ro, p, card)           # files and tables used – for checking again
        if p.get("agent_tool"):
            card["agent"] = {"model": model, "tool": p["agent_tool"], "arguments": p.get("agent_arguments")}
        allowed = list(result_numbers) + list(derived) + [v for r in card["table"]["rows"] for v in r.values() if isinstance(v, (int, float))]
        labels_used = {str(v) for r in card["table"]["rows"] for k, v in r.items() if k.endswith("_label") and v}
        if card.get("chart") and card["chart"].get("data"):
            labels_used |= {str(d.get(card["chart"]["x"])) for d in card["chart"]["data"] if d.get(card["chart"]["x"])}
        context = {"months": [m for m in p.get("months", []) if "-" in str(m)], "extra": [], "labels": sorted(labels_used)}
        cc = claims.check(text, allowed, context) if text else {"passed": True, "checks": 0, "numbers_checked": 0, "failed": 0, "details": []}
        if card.get("explanation"):
            cc["explanation_source"] = "deterministischer Text aus klass_* (statagent/reporting/explain.py), kein Sprachmodell"
        table_values = sum(1 for r in card["table"]["rows"] for v in r.values() if isinstance(v, (int, float)))
        cc["card_values"] = table_values + len(card.get("kpis", []))
        if not cc["passed"]:
            card["text_withheld"] = True
            text = ""
        card["claim_check"] = cc
        emit("card", card)
        if text:
            emit("text", {"markdown": text})
        elif card.get("text_withheld"):
            emit("abstention", {"kind": "nicht prüfbar", "reason": "Der Erläuterungstext enthielt eine nicht belegte Zahl und wird nicht angezeigt; die Karte zeigt nur Werte aus der Abfrage."})
        result_hash = hashlib.sha256(json.dumps(card["table"]["rows"], sort_keys=True, default=str).encode()).hexdigest()
        interpretation = dict(p, readings=readings, handling=handling, free_text=free_text)
        answer_id = _log(conn, user, role, conversation, question, interpretation, [card.get("params")], result_hash, cc, model, text,
                         "metadata" if p["kind"] in ("explain", "definition") else "answer")
        emit("done", {"answer_id": answer_id, "model": model})
        return {"kind": "answer", "answer_id": answer_id, "card": card, "text": text, "params": p}


def _log(conn, user, role, conversation, question, interpretation, tool_calls, result_hash, claim_check, model, text, kind) -> int:
    with conn.transaction():
        return conn.execute("""INSERT INTO ops.answer ("user", role, conversation, question, interpretation, tool_calls, result_hash,
                                 claim_check, model, text, kind) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING answer_id""",
                            (user, role, conversation, question, json.dumps(interpretation, default=str, ensure_ascii=False),
                             json.dumps(tool_calls, default=str, ensure_ascii=False) if tool_calls else None, result_hash,
                             json.dumps(claim_check, ensure_ascii=False) if claim_check else None, model, text, kind)).fetchone()[0]
