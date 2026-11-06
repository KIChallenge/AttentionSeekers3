"""Quality checks of a monthly run → ops.finding, ops.revision, ops.inquiry (task step 3, Anhang A).

Every check is deterministic SQL on store.segment / store.month_record / stat_beschaeftigte of the run's own and
earlier deliveries. A finding carries: level (Satz / Aggregat / Lieferung), German description, extent, 3–5 example
VVH_IDs, a runnable evidence query, its classification and the measure taken:
  explained_plausible     erklärt – plausibel (real development, e.g. seasonality RD-01, Beamte trend RD-02)
  explained_data_problem  erklärt – Datenproblem (cause in the data, rule or assumption applied)
  unexplained             nicht erklärbar (escalated to the Fachabteilung)
Faulty records are never dropped or corrected here; checks only describe and point to the rule that handles them.
"""
import re

from statagent.etl.store import month_bounds
from statagent.qa.run import UNMAPPED, previous_month

MONTH = re.compile(r"^\d{4}-\d{2}$")
SEASONAL_SECTIONS = {"A": "Land- und Forstwirtschaft", "F": "Bau", "I": "Beherbergung und Gastronomie",
                     "R": "Kunst, Unterhaltung und Erholung", "N": "sonstige wirtschaftliche Dienstleistungen",
                     "S": "Kunst, Sport und Erholung / sonstige Dienstleistungen"}
SEASONAL_REGIONS = {"5": "Salzburg", "7": "Tirol"}
JUMP_REL = 0.05          # series change that needs an explanation
JUMP_ABS = 300           # … and at least this many VVH (small series move a lot by chance)
TOTAL_JUMP = 0.03        # total change that needs an explanation
INQUIRY_PROBLEMS = {"DQ-02", "DQ-04", "DQ-16"}


def _ids(conn, sql: str, params=None, n: int = 5) -> list[str]:
    wrapped = f"SELECT vvh_id FROM ({sql}) ids GROUP BY vvh_id ORDER BY length(vvh_id), vvh_id LIMIT {n}"
    return [r[0] for r in conn.execute(wrapped, params).fetchall()]


def _one(conn, sql: str, params=None):
    return conn.execute(sql, params).fetchone()[0]


def _fmt(n) -> str:
    return f"{int(n):,}".replace(",", ".")


def _dec(x: float, digits: int = 2) -> str:
    return f"{x:.{digits}f}".replace(".", ",")


def _pct(x: float, digits: int = 1) -> str:
    """German percentage with sign, e.g. -20,5 %."""
    return f"{x * 100:+.{digits}f} %".replace(".", ",").replace("-", "−")


class Findings:
    def __init__(self, conn, run_id: int, month: str, rule_set: str):
        self.conn, self.run_id, self.month, self.rule_set, self.items = conn, run_id, month, rule_set, []

    def add(self, check_id, problem_id, level, description, extent, examples, sql, classification, measure,
            rule_id=None, inquiry_id=None):
        self.items.append(dict(check_id=check_id, problem_id=problem_id, level=level, description=description,
                               extent=int(extent or 0), example_ids=examples or [], evidence_sql=sql.strip(),
                               classification=classification, measure=measure, rule_id=rule_id, inquiry_id=inquiry_id))

    def save(self):
        for f in self.items:
            self.conn.execute("""INSERT INTO ops.finding (run_id, delivery, rule_set, check_id, problem_id, level, description,
                                   extent, example_ids, evidence_sql, classification, measure, rule_id, inquiry_id)
                                 VALUES (%(run_id)s, %(month)s, %(rule_set)s, %(check_id)s, %(problem_id)s, %(level)s,
                                   %(description)s, %(extent)s, %(example_ids)s, %(evidence_sql)s, %(classification)s,
                                   %(measure)s, %(rule_id)s, %(inquiry_id)s)""",
                              {**f, "run_id": self.run_id, "month": self.month, "rule_set": self.rule_set})


def _rule_state(rules: list[dict], action: str = None, rule_id: str = None, month: str = None) -> dict | None:
    for r in rules:
        if (rule_id and r["rule_id"] == rule_id) or (action and r["action"] == action):
            if month and r["action"] == "carry_forward" and month not in (r["parameters"] or {}).get("deliveries", []):
                continue
            return r
    return None


def _rule_status(conn, rule_id: str) -> str:
    row = conn.execute("SELECT status FROM ops.rule WHERE rule_id = %s", (rule_id,)).fetchone()
    return {"approved": "freigegeben", "proposed": "vorgeschlagen, noch nicht freigegeben",
            "rejected": "abgelehnt", "retired": "außer Kraft"}.get(row[0] if row else None, "nicht vorhanden")


def _stat(conn, rule_set: str, month: str, group: str | None = None) -> dict:
    """Published/own value of a month from stat_beschaeftigte (total, or per dimension code)."""
    if group:
        rows = conn.execute(f"""SELECT {group}, sum(wert) FROM stat_beschaeftigte WHERE regelwerk = %s AND stand = %s
                                GROUP BY 1""", (rule_set, f"Lieferung {month}")).fetchall()
        return {r[0]: int(r[1]) for r in rows}
    v = _one(conn, "SELECT sum(wert) FROM stat_beschaeftigte WHERE regelwerk = %s AND stand = %s",
             (rule_set, f"Lieferung {month}"))
    return {"total": int(v)} if v is not None else {}


# --- record-level and delivery-level checks ----------------------------------------------------

def check_delivery(conn, f: Findings, p: dict, rules: list[dict]):
    m, prev = p["month"], p["prev"]
    rows = _one(conn, "SELECT count(*) FROM store.segment WHERE delivery = %s", (m,))
    prev_rows = _one(conn, "SELECT count(*) FROM store.segment WHERE delivery = %s", (prev,))

    # DQ-01 – swapped BEGINN/ENDE
    dq01 = _one(conn, "SELECT count(*) FROM store.segment WHERE delivery = %s AND 'DQ-01' = ANY(problems)", (m,))
    if dq01:
        sql = f"SELECT vvh_id, beginn, ende FROM roh.lieferung WHERE lieferung = '{m}' AND ((beginn IS NULL AND ende IS NOT NULL) OR ende < beginn)"
        ex = _ids(conn, f"SELECT vvh_id FROM store.segment WHERE delivery = %s AND 'DQ-01' = ANY(problems)", (m,))
        swap = _rule_state(rules, "swap_columns")
        applied = swap and m in (swap["parameters"] or {}).get("deliveries", [])
        if dq01 > 0.5 * rows:
            as_delivered = _one(conn, """SELECT count(DISTINCT vvh_id) FROM store.segment WHERE delivery = %(month)s
                                         AND store.iso_date(begin_raw) <= %(ref)s AND (end_raw IS NULL OR store.iso_date(end_raw) >= %(ref)s)""", p)
            f.add("DQ01", "DQ-01", "delivery",
                  f"BEGINN und ENDE vertauscht: {_fmt(dq01)} von {_fmt(rows)} Sätzen haben leeren BEGINN bei gefülltem ENDE oder ENDE vor BEGINN. "
                  f"Wie geliefert wären am Stichtag nur {_fmt(as_delivered)} Verhältnisse aktiv.",
                  dq01, ex, sql, "explained_data_problem",
                  f"Regel {swap['rule_id']} angewendet: Spalten vertauscht gelesen (gelieferte Werte unverändert)." if applied
                  else f"Regel R-DQ01 {_rule_status(conn, 'R-DQ01')} – gezählt wie geliefert.", "R-DQ01")
        else:
            f.add("DQ01", "DQ-01", "record", f"{_fmt(dq01)} Sätze mit ENDE vor BEGINN oder leerem BEGINN.", dq01, ex, sql,
                  "explained_data_problem", "Gezählt wie geliefert; Sätze im QB ausgewiesen.")

    # DQ-02 – incomplete delivery (drop against the previous delivery, evenly spread)
    if prev_rows and rows < 0.9 * prev_rows:
        missing_sql = f"""SELECT p.vvh_id FROM store.segment p WHERE p.delivery = '{prev}' AND p.counted AND p.effective_end IS NULL
  AND NOT ('DQ-16' = ANY(p.problems))
  AND NOT EXISTS (SELECT 1 FROM store.segment c WHERE c.delivery = '{m}' AND c.vvh_id = p.vvh_id)"""
        missing = _one(conn, f"SELECT count(DISTINCT vvh_id) FROM ({missing_sql}) x")
        ex = _ids(conn, f"SELECT DISTINCT vvh_id FROM ({missing_sql}) x")
        shares = conn.execute("""
            WITH a AS (SELECT delivery, coalesce(bundesland, '') b, count(DISTINCT vvh_id) n FROM store.segment
                       WHERE delivery IN (%(month)s, %(prev)s) AND counted AND effective_end IS NULL GROUP BY 1, 2),
                 s AS (SELECT delivery, b, n::numeric / sum(n) OVER (PARTITION BY delivery) sh FROM a)
            SELECT max(abs(c.sh - p.sh)) FROM s c JOIN s p ON p.b = c.b AND p.delivery = %(prev)s WHERE c.delivery = %(month)s""",
                              p).fetchone()[0] or 0
        carry = _rule_state(rules, "carry_forward", month=m)
        if carry and not (carry["parameters"] or {}).get("qual_suffix"):
            measure = (f"Annahme {carry['rule_id']} angewendet: {_fmt(missing)} in {prev} offene, hier fehlende Verhältnisse "
                       f"mit den Merkmalen aus {prev} gezählt; Revision im nächsten QB.")
        else:
            measure = ("Gezählt wie geliefert (kein Verhältnis aus späteren Lieferungen ergänzt); Annahme R-DQ02 "
                       f"{_rule_status(conn, 'R-DQ02')}; Rückfrage vorbereitet; Revision im nächsten QB.")
        f.add("DQ02", "DQ-02", "delivery",
              f"Lieferung unvollständig: {_fmt(rows)} Sätze statt {_fmt(prev_rows)} im Vormonat ({_pct(rows / prev_rows - 1)}). "
              f"{_fmt(missing)} in {prev} offene Verhältnisse fehlen vollständig. Der Ausfall ist gleich verteilt "
              f"(größte Änderung eines Bundesland-Anteils {_dec(float(shares) * 100)} Prozentpunkte) – kein realer Rückgang.",
              missing, ex, missing_sql, "explained_data_problem", measure, "R-DQ02", "RF-DQ02")

    # DQ-03 – exact duplicates
    dq03 = conn.execute("""SELECT count(*), count(DISTINCT vvh_id) FROM store.segment WHERE delivery = %s AND copy_no > 1""",
                        (m,)).fetchone()
    if dq03[0]:
        f.add("DQ03", "DQ-03", "record",
              f"{_fmt(dq03[0])} exakt doppelte Sätze bei {_fmt(dq03[1])} Verhältnissen.", dq03[0],
              _ids(conn, "SELECT DISTINCT vvh_id FROM store.segment WHERE delivery = %s AND copy_no > 1", (m,)),
              f"SELECT vvh_id, beginn, ende, count(*) FROM roh.lieferung WHERE lieferung = '{m}' GROUP BY vvh_id, person_id, geburtsdatum, geschlecht, beginn, ende, qual, oenace, bundesland HAVING count(*) > 1",
              "explained_data_problem",
              f"Jedes Verhältnis einmal gezählt (Zählregel Z1, Anhang A Regel 1); Kopien gespeichert und markiert; Regel R-DQ03 {_rule_status(conn, 'R-DQ03')}.",
              "R-DQ03")

    # DQ-04 – category missing completely (freie Dienstverträge)
    fd = _one(conn, "SELECT count(*) FROM store.segment WHERE delivery = %s AND qual LIKE '%%FD'", (m,))
    fd_prev = _one(conn, "SELECT count(*) FROM store.segment WHERE delivery = %s AND qual LIKE '%%FD'", (prev,))
    if fd == 0 and fd_prev:
        sql = f"""SELECT DISTINCT p.vvh_id FROM store.segment p WHERE p.delivery = '{prev}' AND p.qual LIKE '%FD' AND p.effective_end IS NULL
  AND NOT ('DQ-16' = ANY(p.problems)) AND NOT EXISTS (SELECT 1 FROM store.segment c WHERE c.delivery = '{m}' AND c.vvh_id = p.vvh_id)"""
        n = _one(conn, f"SELECT count(*) FROM ({sql}) x")
        carry = _rule_state(rules, "carry_forward", month=m)
        measure = (f"Annahme {carry['rule_id']} angewendet: {_fmt(n)} FD-Verhältnisse aus {prev} fortgeschrieben; Revision im nächsten QB."
                   if carry else f"Gezählt wie geliefert; Annahme R-DQ04 {_rule_status(conn, 'R-DQ04')}; Rückfrage vorbereitet.")
        f.add("DQ04", "DQ-04", "delivery",
              f"Keine freien Dienstverträge geliefert ({_fmt(fd_prev)} FD-Sätze im Vormonat, jetzt 0). {_fmt(n)} offene FD-Verhältnisse "
              f"aus {prev} fehlen vollständig. Ein Wegfall einer ganzen Kategorie ist keine reale Entwicklung.",
              n, _ids(conn, f"SELECT vvh_id FROM ({sql}) x"), sql, "explained_data_problem", measure, "R-DQ04", "RF-DQ04")

    # DQ-05/06 – birth dates (counted records)
    for pid, cond, text, rule in (
            ("DQ-05", "'DQ-05' = ANY(problems)", "Geburtsdatum mit Monat 13 (ungültig, Jahr lesbar)", "R-DQ05"),
            ("DQ-06", "'DQ-06' = ANY(problems)", "Geburtsdatum unplausibel (Alter über 110 Jahre)", None)):
        src = ("(SELECT * FROM store.month_record UNION ALL SELECT rule_set, month, vvh_id, person_id, origin, source_delivery, begin_date, "
               "end_date, sex_raw, qual_raw, oenace_raw, bundesland_raw, birth_date_raw, region, oenace, geschlecht, qualifikation, alter, "
               "problems, rules, run_id FROM store.month_excluded) r")
        n = _one(conn, f"SELECT count(*) FROM {src} WHERE rule_set = %s AND month = %s AND {cond}", (f.rule_set, m))
        if not n:
            continue
        ex = _ids(conn, f"SELECT vvh_id FROM {src} WHERE rule_set = %s AND month = %s AND {cond}", (f.rule_set, m))
        sql = f"SELECT vvh_id, birth_date_raw, alter FROM {src} WHERE rule_set = '{f.rule_set}' AND month = '{m}' AND {cond}"
        if pid == "DQ-05":
            swap = _rule_state(rules, "birth_date_swap")
            applied = _rule_state(rules, "age_from_birth_year")
            if swap:
                p_ = swap["parameters"] or {}
                ok = _one(conn, f"SELECT count(*) FROM {src} WHERE rule_set = %s AND month = %s AND {cond} "
                                "AND birth_date_raw ~ '^[0-9]{{4}}-13-(0[1-9]|1[0-2])$'", (f.rule_set, m))
                measure = (f"Falsches Datumsformat markiert; Regel {swap['rule_id']}: " +
                           (f"alle {_fmt(n)} Sätze nach Regel ausgeschlossen (im Überblick ausgewiesen)." if p_.get("exclude") else
                            f"{_fmt(ok)} mit vertauschtem Tag und Monat gelesen, {_fmt(n - ok)} ohne gültigen Tausch (Tag > 12): "
                            + ("Alter = Berichtsjahr − Geburtsjahr." if p_.get("fallback") == "jahr" else "Alter „unbekannt“.")))
                text = "Geburtsdatum mit Monat 13 (falsches Datumsformat)"
            else:
                measure = (f"Regel {applied['rule_id']} angewendet: Alter = Berichtsjahr − Geburtsjahr (wie im Beispielbericht)." if applied
                           else f"Alter „unbekannt“; Regel R-DQ05 (Tag und Monat vertauscht lesen) {_rule_status(conn, 'R-DQ05')}.")
        else:
            measure = "Alter „unbekannt“ (klass_alter: über 110 Jahre); in allen anderen Gliederungen normal gezählt."
        f.add(pid.replace("-", ""), pid, "record", f"{_fmt(n)} gezählte Verhältnisse: {text}.", n, ex, sql,
              "explained_data_problem", measure, rule)

    # DQ-07/08 – codes handled by source mappings
    for pid, cond, text, rule in (
            ("DQ-07", "oenace_raw ~ '^D[A-N]$'", "veralteter ÖNACE-2003-Code (DA–DM)", "R-DQ07"),
            ("DQ-08", "(oenace_raw IS NULL OR bundesland_raw IS NULL)", "OENACE und/oder BUNDESLAND leer", "R-DQ08")):
        n = _one(conn, f"SELECT count(*) FROM store.month_record WHERE rule_set = %s AND month = %s AND {cond}", (f.rule_set, m))
        if not n:
            continue
        ok = _one(conn, f"SELECT count(*) FROM store.month_record WHERE rule_set = %s AND month = %s AND {cond} AND %s = ANY(rules)",
                  (f.rule_set, m, rule))
        f.add(pid.replace("-", ""), pid, "record", f"{_fmt(n)} gezählte Verhältnisse mit {text}.", n,
              _ids(conn, f"SELECT vvh_id FROM store.month_record WHERE rule_set = %s AND month = %s AND {cond}", (f.rule_set, m)),
              f"SELECT vvh_id, oenace_raw, bundesland_raw, oenace, region FROM store.month_record WHERE rule_set = '{f.rule_set}' AND month = '{m}' AND {cond}",
              "explained_data_problem",
              (f"Quellzuordnung nach Regel {rule} ({_fmt(ok)} Verhältnisse): " +
               ("Abschnitt C der im Berichtsmonat gültigen ÖNACE." if pid == "DQ-07" else "Bundesland 0 bzw. Wirtschaftszweig UNB „unbekannt“."))
              if ok == n else f"Regel {rule} {_rule_status(conn, rule)}: {_fmt(n - ok)} Verhältnisse „nicht zuordenbar“ (NZ).", rule)

    # DQ-09/10/11 – segment structure
    for pid, text, rule in (("DQ-09", "überlappende Zeitabschnitte", "R-DQ09"), ("DQ-10", "Lücke zwischen Zeitabschnitten", "R-DQ10"),
                            ("DQ-11", "offener Zeitabschnitt mit Folgeabschnitt", "R-DQ09")):
        n = _one(conn, "SELECT count(DISTINCT vvh_id) FROM store.segment WHERE delivery = %s AND %s = ANY(problems)", (m, pid))
        if n:
            f.add(pid.replace("-", ""), pid, "record", f"{_fmt(n)} Verhältnisse mit {text}.", n,
                  _ids(conn, "SELECT DISTINCT vvh_id FROM store.segment WHERE delivery = %s AND %s = ANY(problems)", (m, pid)),
                  f"SELECT vvh_id, begin_date, end_date, effective_end, qual, oenace, bundesland FROM store.segment WHERE delivery = '{m}' AND vvh_id IN (SELECT vvh_id FROM store.segment WHERE delivery = '{m}' AND '{pid}' = ANY(problems)) ORDER BY vvh_id, begin_date",
                  "explained_data_problem",
                  f"Jedes Verhältnis einmal gezählt, Merkmale aus dem Abschnitt mit dem spätesten Beginn am Stichtag; Regel {rule} {_rule_status(conn, rule)}.",
                  rule)

    # DQ-14 – age heaping at 74
    ages = dict(conn.execute("""SELECT alter, count(*) FROM store.month_record WHERE rule_set = %s AND month = %s
                                AND alter IN ('72', '73', '74', '75') GROUP BY 1""", (f.rule_set, m)).fetchall())
    base = (ages.get("72", 0) + ages.get("73", 0)) / 2
    if base and ages.get("74", 0) > 2.5 * base:
        f.add("DQ14", "DQ-14", "aggregate",
              f"Altershäufung bei 74 Jahren: {_fmt(ages['74'])} Verhältnisse gegenüber {_fmt(ages.get('73', 0))} mit 73 und {_fmt(ages.get('72', 0))} mit 72.",
              ages["74"], _ids(conn, "SELECT vvh_id FROM store.month_record WHERE rule_set = %s AND month = %s AND alter = '74'", (f.rule_set, m)),
              f"SELECT alter, count(*) FROM store.month_record WHERE rule_set = '{f.rule_set}' AND month = '{m}' GROUP BY alter ORDER BY alter",
              "unexplained", "Untersucht, nicht korrigiert (Geburtsdaten wie geliefert); im Beispielbericht ebenso enthalten.")

    # DQ-16 – suspected phantom double registrations (own delivery only) …
    n16 = _one(conn, "SELECT count(*) FROM store.month_record WHERE rule_set = %s AND month = %s AND 'DQ-16' = ANY(problems)", (f.rule_set, m))
    if n16:
        f.add("DQ16", "DQ-16", "record",
              f"{_fmt(n16)} Verdachtsfälle auf Doppelmeldung: neues Verhältnis im Berichtsmonat, obwohl dieselbe Person bereits ein älteres "
              "offenes Verhältnis mit identischer Qualifikation, ÖNACE und Bundesland hat.", n16,
              _ids(conn, "SELECT vvh_id FROM store.month_record WHERE rule_set = %s AND month = %s AND 'DQ-16' = ANY(problems)", (f.rule_set, m)),
              f"SELECT vvh_id, person_id, begin_date, qual_raw, oenace_raw, bundesland_raw FROM store.month_record WHERE rule_set = '{f.rule_set}' AND month = '{m}' AND 'DQ-16' = ANY(problems)",
              "explained_data_problem",
              "Gezählt wie geliefert (wie im Beispielbericht); Bestätigung erst mit der nächsten Lieferung → Revisionsbedarf; Rückfrage vorbereitet.",
              None, "RF-DQ16")
    # … confirmed by this delivery for the previous month
    conf_sql = f"""SELECT r.vvh_id FROM store.month_record r WHERE r.rule_set = '{f.rule_set}' AND r.month = '{prev}' AND 'DQ-16' = ANY(r.problems)
  AND NOT EXISTS (SELECT 1 FROM store.segment c WHERE c.delivery = '{m}' AND c.vvh_id = r.vvh_id)"""
    confirmed = _one(conn, f"SELECT count(*) FROM ({conf_sql}) x")
    if confirmed:
        f.add("DQ16C", "DQ-16", "record",
              f"{_fmt(confirmed)} im Vormonat {prev} gezählte Verdachtsfälle (DQ-16) fehlen in dieser Lieferung vollständig – Doppelmeldung bestätigt.",
              confirmed, _ids(conn, f"SELECT vvh_id FROM ({conf_sql}) x"), conf_sql, "explained_data_problem",
              f"Veröffentlichter Monat {prev} bleibt unverändert; Revisionsbedarf ausgewiesen (Abschnitt 5).", None, "RF-DQ16")

    # DQ-17 – start before the 15th birthday
    n17 = _one(conn, "SELECT count(*) FROM store.segment WHERE delivery = %s AND 'DQ-17' = ANY(problems)", (m,))
    if n17:
        f.add("DQ17", "DQ-17", "record", f"{_fmt(n17)} Zeitabschnitte beginnen vor dem 15. Geburtstag.", n17,
              _ids(conn, "SELECT vvh_id FROM store.segment WHERE delivery = %s AND 'DQ-17' = ANY(problems)", (m,)),
              f"SELECT vvh_id, birth_date, begin_date FROM store.segment WHERE delivery = '{m}' AND 'DQ-17' = ANY(problems)",
              "unexplained", "Plausibilitätshinweis, keine Auswirkung auf die Zählung am Stichtag; nicht korrigiert.")

    # unmapped values (should never happen once all mappings are approved)
    nz = _one(conn, f"""SELECT count(*) FROM store.month_record WHERE rule_set = %s AND month = %s
                        AND %s IN (region, oenace, geschlecht, qualifikation)""", (f.rule_set, m, UNMAPPED))
    if nz:
        f.add("NZ", None, "record", f"{_fmt(nz)} gezählte Verhältnisse mit Werten ohne wirksame Quellzuordnung („nicht zuordenbar“).", nz,
              _ids(conn, "SELECT vvh_id FROM store.month_record WHERE rule_set = %s AND month = %s AND %s IN (region, oenace, geschlecht, qualifikation)",
                   (f.rule_set, m, UNMAPPED)),
              f"SELECT vvh_id, bundesland_raw, oenace_raw, sex_raw, qual_raw FROM store.month_record WHERE rule_set = '{f.rule_set}' AND month = '{m}' AND 'NZ' IN (region, oenace, geschlecht, qualifikation)",
              "unexplained", "Gezählt in der eigenen Zeile „nicht zuordenbar“; Zuordnungsregel nötig (Klassifikation).")


# --- aggregate checks: developments vs. data problems --------------------------------------------

def check_developments(conn, f: Findings, p: dict, delivery_problems: set[str]):
    m, prev = p["month"], p["prev"]
    now, before = _stat(conn, f.rule_set, m), _stat(conn, f.rule_set, prev)
    if not before:
        return
    total, total_prev = now["total"], before["total"]
    change = total / total_prev - 1
    stat_sql = (f"SELECT stand, {{dim}}, sum(wert) FROM stat_beschaeftigte WHERE regelwerk = '{f.rule_set}' "
                f"AND stand IN ('Lieferung {prev}', 'Lieferung {m}') GROUP BY 1, 2 ORDER BY 2, 1")
    data_cause = delivery_problems & {"DQ-01", "DQ-02", "DQ-04"}
    if abs(change) > TOTAL_JUMP:
        f.add("JUMP", None, "aggregate",
              f"Gesamtzahl {_fmt(total_prev)} → {_fmt(total)} ({_pct(change)}) gegenüber dem Vormonat.", abs(total - total_prev), [],
              stat_sql.format(dim="'Insgesamt'"),
              "explained_data_problem" if data_cause else "unexplained",
              f"Ursache in der Lieferung: {', '.join(sorted(data_cause))} (siehe oben)." if data_cause
              else "An die Fachabteilung eskaliert.")
    if m.endswith("-01") and m == "2025-01":
        f.add("RD03", "RD-03", "aggregate",
              "Klassifikationswechsel ÖNACE 2008 → ÖNACE 2025: Ab diesem Berichtsmonat werden die Wirtschaftszweige nach ÖNACE 2025 "
              "ausgewiesen; Abschnitte sind mit dem Vormonat nicht direkt vergleichbar (z. B. J → J/K).", 0, [],
              stat_sql.format(dim="oenace"), "explained_plausible",
              "Zeitreihenbruch ausgewiesen (Fußnote); Vergleich nur über klass_uebergang; Aggregations-Sheet in zwei Blättern.")
    dims = [("region", SEASONAL_REGIONS, "Bundesland"), ("qualifikation", {}, "Qualifikation")]
    if not (m == "2025-01"):
        dims.insert(0, ("oenace", SEASONAL_SECTIONS, "ÖNACE-Abschnitt"))
    collapsed: dict[str, list] = {}
    for dim, seasonal, label_ in dims:
        a, b = _stat(conn, f.rule_set, m, dim), _stat(conn, f.rule_set, prev, dim)
        for code in sorted(set(a) | set(b)):
            x, y = a.get(code, 0), b.get(code, 0)
            if y == 0 and x == 0:
                continue
            rel = (x / y - 1) if y else 1.0
            if abs(rel) <= JUMP_REL or abs(x - y) < JUMP_ABS:
                continue
            rel_to_total = rel - change
            if data_cause:
                collapsed.setdefault(label_, []).append((code, y, x, rel))
                continue
            elif code in seasonal and abs(rel_to_total) < 0.25:
                cls, measure = "explained_plausible", f"Saisonale Entwicklung ({seasonal[code]}, RD-01); nicht korrigiert."
            elif dim == "qualifikation" and code.endswith("FD") and "DQ-04" in delivery_problems:
                cls, measure = "explained_data_problem", "Folge von DQ-04."
            else:
                cls, measure = "unexplained", "Nicht durch Saison oder Lieferfehler erklärt – an die Fachabteilung eskaliert."
            f.add("JUMP_" + dim.upper(), "RD-01" if cls == "explained_plausible" else None, "aggregate",
                  f"{label_} {code}: {_fmt(y)} → {_fmt(x)} ({_pct(rel)}; insgesamt {_pct(change)}).", abs(x - y), [],
                  stat_sql.format(dim=dim), cls, measure)
    for label_, items in collapsed.items():
        rels = [r for *_, r in items]
        dim = {"ÖNACE-Abschnitt": "oenace", "Bundesland": "region", "Qualifikation": "qualifikation"}[label_]
        f.add("JUMP_" + dim.upper(), None, "aggregate",
              f"{len(items)} Ausprägungen der Gliederung {label_} verändern sich um mehr als {int(JUMP_REL * 100)} % "
              f"({_pct(min(rels))} bis {_pct(max(rels))}; insgesamt {_pct(change)}): "
              + ", ".join(f"{c} {_fmt(y)} → {_fmt(x)}" for c, y, x, _ in items[:8]) + ("; …" if len(items) > 8 else "") + ".",
              sum(abs(x - y) for _, y, x, _ in items), [], stat_sql.format(dim=dim), "explained_data_problem",
              f"Gleichmäßige Folge von {', '.join(sorted(data_cause))} – kein realer Rückgang einzelner Bereiche; keine Korrektur.")
    # RD-02 – Beamte trend (a real development, reported once per month as plausible)
    q, q_prev = _stat(conn, f.rule_set, m, "qualifikation").get("Beamte"), _stat(conn, f.rule_set, prev, "qualifikation").get("Beamte")
    if q and q_prev and q < q_prev:
        first = _one(conn, """SELECT sum(wert) FROM stat_beschaeftigte WHERE regelwerk = %s AND qualifikation = 'Beamte'
                              AND stand = (SELECT min(stand) FROM stat_beschaeftigte WHERE regelwerk = %s)""", (f.rule_set, f.rule_set))
        f.add("RD02", "RD-02", "aggregate",
              f"Beamte {_fmt(q_prev)} → {_fmt(q)} ({_pct(q / q_prev - 1, 2)}); seit Beginn der Reihe {_fmt(first)} → {_fmt(q)}.",
              q_prev - q, [], stat_sql.format(dim="qualifikation"), "explained_plausible",
              "Stetiger Rückgang (Pragmatisierungsstopp, Pensionierungen) – reale Entwicklung, nicht korrigiert.")


# --- revision need (Z4, DQ-12) ------------------------------------------------------------------

REVISION_SQL = """
WITH cur AS MATERIALIZED (
  SELECT DISTINCT s.vvh_id FROM store.segment s
  WHERE s.delivery = %(delivery)s AND s.counted AND s.begin_date <= %(ref)s
    AND (s.effective_end IS NULL OR s.effective_end >= CASE WHEN %(whole)s THEN %(start)s ELSE %(ref)s END)
), pub AS MATERIALIZED (
  SELECT vvh_id, origin, 'DQ-16' = ANY(problems) AS dq16 FROM store.month_record WHERE rule_set = %(rule_set)s AND month = %(month)s
), j AS MATERIALIZED (
  -- FULL JOIN on equality: always a hash or merge join (never quadratic, also on fresh rows without statistics)
  SELECT coalesce(c.vvh_id, p.vvh_id) AS vvh_id, c.vvh_id IS NOT NULL AS in_cur, p.vvh_id IS NOT NULL AS in_pub, p.origin, p.dq16
  FROM cur c FULL JOIN pub p ON p.vvh_id = c.vvh_id
), newv AS (
  SELECT vvh_id FROM j WHERE in_cur AND NOT in_pub
)
SELECT count(*) FILTER (WHERE in_pub), count(*) FILTER (WHERE in_cur),
       count(*) FILTER (WHERE in_cur AND NOT in_pub),
       count(*) FILTER (WHERE in_pub AND NOT in_cur),
       count(*) FILTER (WHERE in_pub AND NOT in_cur AND dq16),
       count(*) FILTER (WHERE origin = 'carry_forward'),
       count(*) FILTER (WHERE origin = 'carry_forward' AND in_cur),
       (SELECT count(*) FROM newv
        WHERE NOT EXISTS (SELECT 1 FROM store.segment d WHERE d.delivery = %(month)s AND d.vvh_id = newv.vvh_id)
          AND EXISTS (SELECT 1 FROM store.segment o WHERE o.delivery = %(month_prev)s AND o.vvh_id = newv.vvh_id AND o.effective_end IS NULL))
FROM j
"""


def check_revisions(conn, f: Findings, p: dict, findings_by_month: dict) -> None:
    """Earlier months contained in this delivery (the two previous months) vs. their published value."""
    m = p["month"]
    earlier = previous_month(m)
    for month in (earlier, previous_month(earlier)):
        if not _stat(conn, f.rule_set, month):
            continue
        start, ref = month_bounds(month)
        pub, cur, new, gone, gone16, carried, confirmed, missing = conn.execute(REVISION_SQL, {
            "delivery": m, "ref": ref, "start": start, "whole": p["r_whole_month"] is not None,
            "rule_set": f.rule_set, "month": month, "month_prev": previous_month(month)}).fetchone()
        causes = []
        problems = findings_by_month.get(month, set())
        defect = problems & {"DQ-02", "DQ-04"}
        if defect and missing:
            causes.append(f"{_fmt(missing)} Verhältnisse fehlten in der Lieferung des veröffentlichten Monats "
                          f"({'DQ-02 unvollständige Lieferung' if 'DQ-02' in defect else 'DQ-04 fehlende freie Dienstverträge'})")
            new -= missing
        if carried:
            causes.append(f"Annahme bestätigt für {_fmt(confirmed)} von {_fmt(carried)} fortgeschriebenen Verhältnissen")
        if gone16:
            causes.append(f"{_fmt(gone16)} Doppelmeldungen (DQ-16) entfallen")
        if new:
            causes.append(f"{_fmt(new)} Nachmeldungen (DQ-12)")
        if gone - gone16:
            causes.append(f"{_fmt(gone - gone16)} rückwirkende Abmeldungen/Korrekturen (DQ-12)")
        if "DQ-04" in findings_by_month.get(m, set()):
            causes.append("diese Lieferung ohne freie Dienstverträge (DQ-04): Differenz ist ein Artefakt")
        if "DQ-02" in findings_by_month.get(m, set()):
            causes.append("diese Lieferung unvollständig (DQ-02): Differenz ist ein Artefakt")
        conn.execute("""INSERT INTO ops.revision (run_id, rule_set, month, delivery, published, current, new_vvh, vanished_vvh,
                          vanished_dq16, carried_total, carried_confirmed, main_cause)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                     (f.run_id, f.rule_set, month, m, pub, cur, new, gone, gone16, carried, confirmed, "; ".join(causes) or "keine Abweichung"))


def ensure_inquiries(conn, f: Findings) -> None:
    """One Rückfrage per problem (first month it appears), with evidence from the finding (Anhang A 3)."""
    texts = {
        "RF-DQ02": ("Die Lieferung 2025-10 enthält rund 20 % weniger Sätze als die Nachbarlieferungen; der Ausfall ist über alle "
                    "Merkmale gleich verteilt. Ist die Lieferung unvollständig, und gibt es eine Nachlieferung?",
                    "Zuvor offene, jetzt fehlende Verhältnisse mit den Merkmalen der Vorlieferung fortschreiben (Regel R-DQ02); "
                    "veröffentlichte Zahl als Annahme kennzeichnen, Revision mit der Lieferung 2025-11."),
        "RF-DQ04": ("In der Lieferung 2025-03 fehlen alle freien Dienstverträge (ArbeiterFD, AngestellteFD), im Folgemonat sind sie "
                    "wieder da. Wurden sie technisch nicht mitgeliefert?",
                    "Offene FD-Verhältnisse aus 2025-02 fortschreiben (Regel R-DQ04); Revision im QB 2025-04."),
        "RF-DQ16": ("Jeden Monat melden rund 200 Personen ein zweites, neues Verhältnis mit identischen Merkmalen zu einem bestehenden; "
                    "diese Verhältnisse fehlen in der nächsten Lieferung vollständig. Handelt es sich um Doppelmeldungen, die nicht "
                    "gezählt werden sollen?",
                    "Bis zur Antwort wie geliefert zählen (wie im Beispielbericht), Verdachtsfälle im QB ausweisen und mit der "
                    "nächsten Lieferung als Revisionsbedarf bestätigen; nach Antwort als Leseregel umsetzen."),
    }
    for item in f.items:
        iid = item["inquiry_id"]
        if not iid or iid not in texts:
            continue
        if conn.execute("SELECT 1 FROM ops.inquiry WHERE inquiry_id = %s", (iid,)).fetchone():
            continue
        question, proposal = texts[iid]
        conn.execute("""INSERT INTO ops.inquiry (inquiry_id, delivery, problem_id, question, proposal, extent, example_ids,
                          evidence_sql, asked_on) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL)""",
                     (iid, f.month, item["problem_id"], question, proposal, item["extent"], item["example_ids"], item["evidence_sql"]))


def run_checks(conn, run_id: int, month: str, rule_set: str, params: dict, rules: list[dict]) -> list[dict]:
    if not MONTH.match(month):
        raise ValueError(f"Berichtsmonat {month!r} hat nicht das Format JJJJ-MM")
    f = Findings(conn, run_id, month, rule_set)
    check_delivery(conn, f, params, rules)
    delivery_problems = {i["problem_id"] for i in f.items if i["level"] == "delivery"}
    check_developments(conn, f, params, delivery_problems)
    by_month = {}
    for d, pid in conn.execute("""SELECT f.delivery, f.problem_id FROM ops.finding f JOIN ops.run r USING (run_id)
                                  WHERE f.rule_set = %s AND f.level = 'delivery' AND r.status = 'done'""", (rule_set,)).fetchall():
        by_month.setdefault(d, set()).add(pid)
    by_month[month] = delivery_problems
    check_revisions(conn, f, params, by_month)
    f.save()
    ensure_inquiries(conn, f)
    return f.items
