"""Monthly production run: `lauf --lieferung JJJJ-MM` (Fachbeschreibung §2a, §4; task step 3).

One run = one delivery. It reads only store.segment of its own delivery (and, for an approved carry-forward
assumption, the previous delivery – never a later one), applies the approved rules of its rule set and writes:

- store.month_record   one row per counted VVH with the codes used (evidence for every number)
- stat_beschaeftigte   the month's values in long format (Anhang B), status 'vorlaeufig' until published
- ops.run / ops.run_metric   applied rules, reconciliation figures, checksum (T1)
- ops.finding, ops.inquiry, the quality report (statagent/qa/checks.py, statagent/qa/report.py)

Counting rules (rule set 'basis' = Fachbeschreibung Z1–Z8):
  Z1 unit = VVH, each VVH once · Z2 a segment exists on the Stichtag · Z3 attributes from that segment ·
  Z4 own delivery · Z5 age in completed years on the Stichtag · Z6 category = Qualifikation ·
  Z7 ÖNACE valid in the month (via quellzuordnung_wirksam) · Z8 missing values via approved rules, nothing lost.
Rule set 'auftraege' adds the approved counting rules of the change orders (actions 'whole_month',
'category_level'); all reading rules of 'basis' keep applying.

Gates (the run fails instead of publishing wrong numbers):
  - every VVH active on the Stichtag in the delivery is counted exactly once (no relationship lost)
  - stat total = counted records; every dimension sums to the same total
  - read rows = counted + not counted + excluded rows
Values without an effective source mapping go to the visible code 'NZ' (nicht zuordenbar) and a finding.
"""
import datetime as dt
import hashlib

from statagent.config import connect, setup_logging
from statagent.etl.store import month_bounds

SOURCE = "ZVD-Monatslieferung"
RULE_SETS = ("basis", "auftraege")
RUN_ACTIONS = ("swap_columns", "count_duplicates_once", "trim_overlap", "close_gap", "source_mapping", "birth_date_swap",
               "carry_forward", "age_from_birth_year", "whole_month", "category_level", "age_groups")
UNMAPPED = "NZ"
DIMENSIONS = ("region", "oenace", "geschlecht", "qualifikation", "alter")


class RunError(RuntimeError):
    """A gate failed: nothing of the run is kept."""


def previous_month(month: str) -> str:
    year, mon = map(int, month.split("-"))
    return f"{year - 1}-12" if mon == 1 else f"{year}-{mon - 1:02d}"


def run_rules(conn, rule_set: str, extra: tuple[str, ...] = ()) -> list[dict]:
    """Approved rules of 'basis' (+ the given rule set), plus `extra` proposed rules for a preview."""
    sets = ["basis"] if rule_set == "basis" else ["basis", rule_set]
    cur = conn.execute("""SELECT rule_id, action, parameters, rule_set, approved_by, approved_at, title
                          FROM ops.rule WHERE rule_set = ANY(%s) AND action = ANY(%s)
                            AND (status = 'approved' OR rule_id = ANY(%s)) ORDER BY rule_id""",
                       (sets, list(RUN_ACTIONS), list(extra)))
    return [dict(zip(("rule_id", "action", "parameters", "rule_set", "approved_by", "approved_at", "title"), r))
            for r in cur.fetchall()]


def run_params(rules: list[dict], month: str) -> dict:
    """SQL parameters derived from the rules (rule ID or NULL per action) for one month."""
    params = {"r_carry": None, "carry_suffix": "", "r_age_year": None, "r_whole_month": None,
              "r_category": None, "category_version": None, "category_preview": False,
              "r_bswap": None, "bswap_fallback": "unbekannt", "bswap_exclude": False}
    for r in rules:
        p = r["parameters"] or {}
        if r["action"] == "carry_forward" and month in p.get("deliveries", []):
            params["r_carry"], params["carry_suffix"] = r["rule_id"], p.get("qual_suffix", "")
        elif r["action"] == "age_from_birth_year":
            params["r_age_year"] = r["rule_id"]
        elif r["action"] == "birth_date_swap":
            params["r_bswap"] = r["rule_id"]
            params["bswap_fallback"] = p.get("fallback", "unbekannt")          # unbekannt | jahr
            params["bswap_exclude"] = bool(p.get("exclude", False))            # True: month-13 records are not counted
        elif r["action"] == "whole_month":
            params["r_whole_month"] = r["rule_id"]
        elif r["action"] == "category_level":
            params["r_category"], params["category_version"] = r["rule_id"], p.get("version", "Beschaeftigungskategorie")
    return params


# Selection of the counted segment per VVH. Stichtag (Z2/Z3): segment valid on the Stichtag.
# Whole month (order 2): any segment with at least one day in the month; attributes from the last one.
# Ties (exact duplicate copies, DQ-03) are broken deterministically; each VVH appears once (Z1).
SELECT_SQL = """
WITH active AS (
  SELECT DISTINCT ON (s.vvh_id) s.vvh_id, s.person_id, s.delivery, s.begin_date, s.effective_end, s.sex, s.qual,
         s.oenace, s.bundesland, s.birth_date_raw, s.birth_date, s.birth_year, s.problems, s.rules,
         'delivery'::text AS origin
  FROM store.segment s
  WHERE s.delivery = %(month)s AND s.counted
    AND s.begin_date <= %(ref)s
    AND (s.effective_end IS NULL OR s.effective_end >= CASE WHEN %(r_whole_month)s::text IS NULL THEN %(ref)s ELSE %(month_start)s END)
  ORDER BY s.vvh_id, s.begin_date DESC, s.effective_end DESC NULLS FIRST, s.copy_no, s.qual, s.oenace, s.bundesland
), carried AS (
  -- Assumption rule (carry_forward, e.g. R-DQ02/R-DQ04): open in the previous delivery, absent from this one.
  SELECT DISTINCT ON (p.vvh_id) p.vvh_id, p.person_id, p.delivery, p.begin_date, p.effective_end, p.sex, p.qual,
         p.oenace, p.bundesland, p.birth_date_raw, p.birth_date, p.birth_year, p.problems, p.rules || %(r_carry)s::text,
         'carry_forward'::text
  FROM store.segment p
  WHERE %(r_carry)s::text IS NOT NULL AND p.delivery = %(prev)s AND p.counted
    AND p.begin_date <= %(prev_ref)s AND p.effective_end IS NULL
    AND NOT ('DQ-16' = ANY(p.problems))
    AND (%(carry_suffix)s = '' OR p.qual LIKE '%%' || %(carry_suffix)s)
    AND NOT EXISTS (SELECT 1 FROM store.segment c WHERE c.delivery = %(month)s AND c.vvh_id = p.vvh_id)
  ORDER BY p.vvh_id, p.begin_date DESC, p.copy_no, p.qual, p.oenace, p.bundesland
), picked AS (
  SELECT * FROM active UNION ALL SELECT * FROM carried
), aged AS (
  SELECT p.*,
         CASE WHEN p.birth_date IS NOT NULL THEN extract(year FROM age(%(ref)s::date, p.birth_date))::int
              -- R-DQ05 (birth_date_swap): JJJJ-13-TT read as JJJJ-TT-13 where TT is a valid month
              WHEN %(r_bswap)s::text IS NOT NULL AND p.birth_date_raw ~ '^[0-9]{4}-13-(0[1-9]|1[0-2])$'
                   THEN extract(year FROM age(%(ref)s::date, make_date(p.birth_year, substr(p.birth_date_raw, 9, 2)::int, 13)))::int
              WHEN %(r_bswap)s::text IS NOT NULL AND %(bswap_fallback)s = 'jahr' AND p.birth_year IS NOT NULL
                   AND p.birth_date_raw ~ '^[0-9]{4}-13-' THEN %(year)s - p.birth_year
              WHEN %(r_age_year)s::text IS NOT NULL AND p.birth_year IS NOT NULL THEN %(year)s - p.birth_year END AS age_years
  FROM picked p
), mapped AS (
  SELECT a.*,
         qb.code AS c_region, qb.regel_id AS m_region,
         qo.code AS c_oenace, qo.regel_id AS m_oenace,
         qg.code AS c_sex, qg.regel_id AS m_sex,
         qq.code AS c_qual, qq.regel_id AS m_qual,
         CASE WHEN a.age_years IS NULL THEN 'UNB'
              WHEN ka.code IS NULL THEN 'UNB'          -- outside klass_alter (age > 110, DQ-06): unbekannt
              ELSE ka.code END AS c_age
  FROM aged a
  LEFT JOIN quellzuordnung_wirksam qb ON qb.quelle = %(source)s AND qb.merkmal = 'BUNDESLAND'
       AND qb.quellwert = coalesce(a.bundesland, '') AND %(ref)s BETWEEN qb.gueltig_von AND coalesce(qb.gueltig_bis, 'infinity')
  LEFT JOIN quellzuordnung_wirksam qo ON qo.quelle = %(source)s AND qo.merkmal = 'OENACE'
       AND qo.quellwert = coalesce(a.oenace, '') AND %(ref)s BETWEEN qo.gueltig_von AND coalesce(qo.gueltig_bis, 'infinity')
  LEFT JOIN quellzuordnung_wirksam qg ON qg.quelle = %(source)s AND qg.merkmal = 'GESCHLECHT'
       AND qg.quellwert = coalesce(a.sex, '') AND %(ref)s BETWEEN qg.gueltig_von AND coalesce(qg.gueltig_bis, 'infinity')
  LEFT JOIN quellzuordnung_wirksam qq ON qq.quelle = %(source)s AND qq.merkmal = 'QUAL'
       AND qq.quellwert = coalesce(a.qual, '') AND %(ref)s BETWEEN qq.gueltig_von AND coalesce(qq.gueltig_bis, 'infinity')
  LEFT JOIN klass_alter ka ON ka.version = '-' AND ka.ebene = 'Altersjahr' AND ka.code = a.age_years::text
), categorised AS (
  -- Order 1 (category_level): Qualifikation -> Beschäftigungskategorie, taken from klass_qualifikation (data, T3).
  SELECT m.*, CASE WHEN %(r_category)s::text IS NULL THEN m.c_qual
                   WHEN %(category_preview)s THEN (SELECT coalesce(k.attribute->>'beschaeftigungskategorie', k.code)
                         FROM klass_qualifikation k WHERE k.version = '-' AND k.code = m.c_qual)
                   ELSE (SELECT c.code FROM klass_qualifikation k
                         JOIN klass_qualifikation c ON c.version = %(category_version)s
                              AND c.code = coalesce(k.attribute->>'beschaeftigungskategorie', k.code)
                         WHERE k.version = '-' AND k.code = m.c_qual)
              END AS c_qual_out
  FROM mapped m
)
INSERT INTO store.month_record (rule_set, month, vvh_id, person_id, origin, source_delivery, begin_date, end_date,
  sex_raw, qual_raw, oenace_raw, bundesland_raw, birth_date_raw, region, oenace, geschlecht, qualifikation, alter,
  problems, rules, run_id)
SELECT %(rule_set)s, %(month)s, vvh_id, person_id, origin, delivery, begin_date, effective_end,
       sex, qual, oenace, bundesland, birth_date_raw,
       coalesce(c_region, %(unmapped)s), coalesce(c_oenace, %(unmapped)s), coalesce(c_sex, %(unmapped)s),
       coalesce(c_qual_out, %(unmapped)s), c_age,
       problems,
       array_remove(ARRAY(SELECT DISTINCT x FROM unnest(rules || ARRAY[m_region, m_oenace, m_sex, m_qual,
            CASE WHEN birth_date IS NULL AND age_years IS NOT NULL THEN %(r_age_year)s::text END,
            CASE WHEN birth_date IS NULL AND birth_date_raw ~ '^[0-9]{4}-13-' THEN %(r_bswap)s::text END,
            %(r_whole_month)s::text, %(r_category)s::text]) AS x ORDER BY x), NULL),
       %(run_id)s
FROM categorised
"""

STAT_SQL = """
INSERT INTO stat_beschaeftigte (regelwerk, zeitraum_art, zeitraum_von, zeitraum_bis, region, oenace, geschlecht,
  qualifikation, alter, variable, wert, status, stand, lauf_id)
SELECT %(rule_set)s, %(period_kind)s, %(period_from)s, %(ref)s, region, oenace, geschlecht, qualifikation, alter,
       'Beschaeftigungsverhaeltnisse', count(*), 'vorlaeufig', 'Lieferung ' || %(month)s, %(run_id)s
FROM store.month_record WHERE rule_set = %(rule_set)s AND month = %(month)s
GROUP BY region, oenace, geschlecht, qualifikation, alter
"""

# Reconciliation of the delivery rows (QB overview): read = counted + not counted + excluded.
RECONCILE_SQL = """
WITH rows AS (
  SELECT s.vvh_id, s.counted,
         s.begin_date <= %(ref)s AND (s.effective_end IS NULL OR s.effective_end >=
             CASE WHEN %(r_whole_month)s::text IS NULL THEN %(ref)s ELSE %(month_start)s END) AS in_period
  FROM store.segment s WHERE s.delivery = %(month)s
)
SELECT count(*) AS rows_read,
       count(*) FILTER (WHERE in_period AND counted) AS rows_in_period,
       count(*) FILTER (WHERE in_period AND NOT counted) AS rows_excluded_rule,
       count(*) FILTER (WHERE NOT in_period OR in_period IS NULL) AS rows_not_counted,
       count(DISTINCT vvh_id) FILTER (WHERE in_period AND counted) AS vvh_in_period,
       count(DISTINCT vvh_id) AS vvh_read
FROM rows
"""


FLOW_SQL = """
INSERT INTO store.month_flow (rule_set, month, kind, region, oenace, geschlecht, qualifikation, alter, n, run_id)
SELECT %(rule_set)s, %(month)s, 'zu', region, oenace, geschlecht, qualifikation, alter, count(*), %(run_id)s
FROM store.month_record c WHERE c.rule_set = %(rule_set)s AND c.month = %(month)s
  AND NOT EXISTS (SELECT 1 FROM store.month_record o WHERE o.rule_set = %(rule_set)s AND o.month = %(prev)s AND o.vvh_id = c.vvh_id)
GROUP BY 4, 5, 6, 7, 8
UNION ALL
SELECT %(rule_set)s, %(month)s, 'ab', region, oenace, geschlecht, qualifikation, alter, count(*), %(run_id)s
FROM store.month_record o WHERE o.rule_set = %(rule_set)s AND o.month = %(prev)s
  AND NOT EXISTS (SELECT 1 FROM store.month_record c WHERE c.rule_set = %(rule_set)s AND c.month = %(month)s AND c.vvh_id = o.vvh_id)
GROUP BY 4, 5, 6, 7, 8
"""


def refresh_flows(conn, rule_set: str, month: str, run_id: int) -> None:
    """Zu-/Abgänge of `month` against the previous month (only if both months are computed in this rule set)."""
    prev = previous_month(month)
    conn.execute("DELETE FROM store.month_flow WHERE rule_set = %s AND month = %s", (rule_set, month))
    both = conn.execute("""SELECT count(DISTINCT month) FROM (SELECT month FROM store.month_record WHERE rule_set = %s AND month = %s LIMIT 1) a
                           UNION ALL SELECT count(*) FROM (SELECT 1 FROM store.month_record WHERE rule_set = %s AND month = %s LIMIT 1) b""",
                        (rule_set, month, rule_set, prev)).fetchall()
    if all(r[0] for r in both):
        # set operations on two months of ~400k rows: hash anti-joins; a nested loop on fresh rows without statistics
        # (first run of a rule set) would be quadratic
        conn.execute("SET LOCAL enable_nestloop = off")
        conn.execute(FLOW_SQL, {"rule_set": rule_set, "month": month, "prev": prev, "run_id": run_id})
        conn.execute("SET LOCAL enable_nestloop = on")


def month_checksum(conn, rule_set: str, month: str) -> str:
    """md5 over the month's stat rows and counted records in a fixed order (T1: same data + rules → same value)."""
    stat = conn.execute("""SELECT md5(coalesce(string_agg(concat_ws(';', zeitraum_art, zeitraum_von, zeitraum_bis, region,
                                  oenace, geschlecht, qualifikation, alter, variable, wert), '|'
                                  ORDER BY zeitraum_art, region, oenace, geschlecht, qualifikation, alter, variable), ''))
                           FROM stat_beschaeftigte WHERE regelwerk = %s AND stand = %s""",
                        (rule_set, f"Lieferung {month}")).fetchone()[0]
    records = conn.execute("""SELECT md5(coalesce(string_agg(concat_ws(';', vvh_id, origin, source_delivery, region, oenace,
                                     geschlecht, qualifikation, alter, array_to_string(rules, ',')), '|' ORDER BY vvh_id), ''))
                              FROM store.month_record WHERE rule_set = %s AND month = %s""", (rule_set, month)).fetchone()[0]
    return hashlib.md5(f"{stat}{records}".encode()).hexdigest()


def _gates(conn, rule_set: str, month: str, p: dict, metrics: dict) -> list[str]:
    """Checks that must hold for the run to be kept. Returns the failures (German)."""
    failures = []
    total_records = metrics["records_total"]
    stat_total = conn.execute("SELECT coalesce(sum(wert), 0) FROM stat_beschaeftigte WHERE regelwerk = %s AND stand = %s",
                              (rule_set, f"Lieferung {month}")).fetchone()[0]
    if int(stat_total) != total_records:
        failures.append(f"Summe stat_beschaeftigte = {stat_total} ≠ {total_records} gezählte Verhältnisse")
    dims = conn.execute("""SELECT count(DISTINCT region), count(*) FILTER (WHERE region IS NULL OR oenace IS NULL OR
                                  geschlecht IS NULL OR qualifikation IS NULL OR alter IS NULL)
                           FROM store.month_record WHERE rule_set = %s AND month = %s""", (rule_set, month)).fetchone()
    if dims[1]:
        failures.append(f"{dims[1]} gezählte Verhältnisse ohne Code")
    lost = conn.execute("""
        SELECT count(DISTINCT s.vvh_id) FROM store.segment s
        WHERE s.delivery = %(month)s AND s.begin_date <= %(ref)s
          AND (s.effective_end IS NULL OR s.effective_end >= CASE WHEN %(r_whole_month)s::text IS NULL THEN %(ref)s ELSE %(month_start)s END)
          AND NOT EXISTS (SELECT 1 FROM store.month_record m WHERE m.rule_set = %(rule_set)s AND m.month = %(month)s
                          AND m.vvh_id = s.vvh_id)
          AND NOT EXISTS (SELECT 1 FROM store.month_excluded x WHERE x.rule_set = %(rule_set)s AND x.month = %(month)s
                          AND x.vvh_id = s.vvh_id)""", p).fetchone()[0]
    if lost:
        failures.append(f"{lost} am Stichtag bestehende Verhältnisse nicht gezählt (Anhang A Regel 1)")
    dup = conn.execute("""SELECT count(*) - count(DISTINCT vvh_id) FROM store.month_record
                          WHERE rule_set = %s AND month = %s""", (rule_set, month)).fetchone()[0]
    if dup:
        failures.append(f"{dup} Verhältnisse mehrfach gezählt (Zählregel Z1)")
    if metrics["rows_read"] != metrics["rows_counted"] + metrics["rows_not_counted"] + metrics["rows_excluded"]:
        failures.append("Abrechnung gelesen = gezählt + nicht gezählt + ausgeschlossen geht nicht auf")
    if metrics["records_delivery"] + metrics["records_excluded_rule"] != metrics["vvh_in_period"]:
        failures.append(f"{metrics['vvh_in_period']} Verhältnisse im Zeitraum, aber {metrics['records_delivery']} gezählt "
                        f"+ {metrics['records_excluded_rule']} nach Regel ausgeschlossen")
    return failures


def published(conn, rule_set: str, month: str) -> str | None:
    """Checksum of the published (status 'endgueltig') month, if any."""
    row = conn.execute("""SELECT r.checksum FROM ops.run r WHERE r.run_id = (
                            SELECT max(lauf_id) FROM stat_beschaeftigte WHERE regelwerk = %s AND stand = %s
                            AND status = 'endgueltig')""", (rule_set, f"Lieferung {month}")).fetchone()
    return row[0] if row else None


def run_month(conn, month: str, rule_set: str = "basis", preview: tuple[str, ...] = (), log=None,
              progress=None, write_files: bool = True) -> dict:
    """One production run inside the caller's transaction. Returns the run summary.

    `progress(step, pct, detail)` is called for live progress (CLI log, SSE stream in the web UI).
    `write_files=False`: no QB/Rückfrage files (callers that roll the transaction back, e.g. tests)."""
    log = log or setup_logging("lauf")
    say = progress or (lambda *a: None)
    conn.execute("SET LOCAL work_mem = '256MB'")     # sorts and hashes of ~400k VVH per month stay in memory
    if rule_set not in RULE_SETS:
        raise ValueError(f"Regelwerk {rule_set!r} unbekannt – möglich: {', '.join(RULE_SETS)}")
    loaded = conn.execute("SELECT zeilen FROM roh.ladeprotokoll WHERE lieferung = %s", (month,)).fetchone()
    if not loaded:
        raise ValueError(f"Lieferung {month} ist nicht geladen")
    rules = run_rules(conn, rule_set, preview)
    month_start, ref = month_bounds(month)
    category_level_built = conn.execute("""SELECT 1 FROM klass_qualifikation WHERE version = (SELECT coalesce(parameters->>'version',
        'Beschaeftigungskategorie') FROM ops.rule WHERE action = 'category_level' ORDER BY rule_id DESC LIMIT 1) LIMIT 1""").fetchone()
    prev = previous_month(month)
    _, prev_ref = month_bounds(prev)
    params = {"month": month, "month_start": month_start, "ref": ref, "prev": prev, "prev_ref": prev_ref,
              "year": ref.year, "rule_set": rule_set, "source": SOURCE, "unmapped": UNMAPPED, **run_params(rules, month)}
    if params["r_category"] and not category_level_built:
        if params["r_category"] not in preview:
            raise RunError(f"Regel {params['r_category']} ist freigegeben, aber die Klassifikation hat die Ebene noch nicht – zuerst "
                           "`python -m statagent klassifikation` (Klassifikation vor Reporting, Änderungsauftrag 1)")
        params["category_preview"] = True     # preview only: category straight from the qualifikation.csv attribute
    whole_month = params["r_whole_month"] is not None
    params["period_kind"], params["period_from"] = ("Monat", month_start) if whole_month else ("Stichtag", ref)
    applied = sorted({r["rule_id"] for r in rules})
    run_id = conn.execute("""INSERT INTO ops.run (kind, delivery, rule_set, rules, note) VALUES ('month', %s, %s, %s, %s)
                             RETURNING run_id""",
                          (month, rule_set, applied, f"Vorschau mit {', '.join(preview)}" if preview else None)).fetchone()[0]
    params["run_id"] = run_id
    say("start", 5, f"Lauf {run_id}: Lieferung {month} wird gelesen ({loaded[0]:,} Sätze)".replace(",", "."))
    log.info("%srun %s: delivery %s, rule set %s, rules %s", "PREVIEW " if preview else "", run_id, month, rule_set, applied)

    frozen = published(conn, rule_set, month)          # before the old rows are replaced
    conn.execute("DELETE FROM store.month_record WHERE rule_set = %s AND month = %s", (rule_set, month))
    conn.execute("DELETE FROM stat_beschaeftigte WHERE regelwerk = %s AND stand = %s", (rule_set, f"Lieferung {month}"))
    conn.execute(SELECT_SQL, params)
    conn.execute("DELETE FROM store.month_excluded WHERE rule_set = %s AND month = %s", (rule_set, month))
    if params["r_bswap"] and params["bswap_exclude"]:
        # R-DQ05 with exclude = true: month-13 records are not counted, but kept and shown as excluded (never silently lost)
        conn.execute("""WITH moved AS (DELETE FROM store.month_record WHERE rule_set = %(rule_set)s AND month = %(month)s
                                       AND birth_date_raw ~ '^[0-9]{4}-13-' RETURNING *)
                        INSERT INTO store.month_excluded SELECT moved.*, %(r_bswap)s FROM moved""", params)
    conn.execute("ANALYZE store.month_record")   # fresh rows (e.g. first run of a rule set) need statistics for the checks below
    say("select", 45, "Zählregeln angewendet, Merkmale zugeordnet")
    conn.execute(STAT_SQL, params)
    say("aggregate", 60, "stat_beschaeftigte geschrieben")

    cur = conn.execute(RECONCILE_SQL, params)
    rec = dict(zip([c.name for c in cur.description], cur.fetchone()))
    counts = conn.execute("""SELECT count(*), count(*) FILTER (WHERE origin = 'delivery'),
                                    count(*) FILTER (WHERE origin = 'carry_forward'),
                                    count(*) FILTER (WHERE %s IN (region, oenace, geschlecht, qualifikation)),
                                    count(*) FILTER (WHERE alter = 'UNB')
                             FROM store.month_record WHERE rule_set = %s AND month = %s""",
                          (UNMAPPED, rule_set, month)).fetchone()
    metrics = {
        "rows_read": rec["rows_read"],
        "rows_counted": counts[1],                                  # one row per counted VVH
        "rows_excluded": rec["rows_in_period"] - counts[1] + rec["rows_excluded_rule"],
        "rows_not_counted": rec["rows_not_counted"],
        "vvh_read": rec["vvh_read"], "vvh_in_period": rec["vvh_in_period"],
        "records_total": counts[0], "records_delivery": counts[1], "records_carried": counts[2],
        "records_unmapped": counts[3], "records_age_unknown": counts[4],
        "records_excluded_rule": conn.execute("""SELECT count(*) FROM store.month_excluded WHERE rule_set = %s AND month = %s
                                                 AND origin = 'delivery'""", (rule_set, month)).fetchone()[0],
    }
    failures = _gates(conn, rule_set, month, params, metrics)
    say("gates", 70, f"Prüfungen: {6 - len(failures)}/6 bestanden")
    if failures:
        raise RunError(f"Lauf {run_id} ({month}, {rule_set}) abgebrochen: " + "; ".join(failures))

    checksum = month_checksum(conn, rule_set, month)
    if frozen and frozen != checksum and not preview:
        raise RunError(f"Monat {month} ({rule_set}) ist veröffentlicht (Prüfsumme {frozen[:8]}…); der neue Lauf ergäbe "
                       f"{checksum[:8]}… – veröffentlichte Monate werden nicht geändert (Zählregel Z4). Abweichungen "
                       "stehen als Revisionsbedarf im Qualitätsbericht.")
    if frozen == checksum:
        conn.execute("UPDATE stat_beschaeftigte SET status = 'endgueltig' WHERE regelwerk = %s AND stand = %s",
                     (rule_set, f"Lieferung {month}"))
    for key, value in metrics.items():
        conn.execute("INSERT INTO ops.run_metric VALUES (%s, %s, %s)", (run_id, key, value))
    conn.execute("""UPDATE ops.run SET status = 'done', finished_at = now(), row_count = %s, checksum = %s WHERE run_id = %s""",
                 (metrics["records_total"], checksum, run_id))
    log.info("  %s %s: %s counted (%s carried forward), checksum %s", month, rule_set,
             f"{metrics['records_total']:,}", f"{metrics['records_carried']:,}", checksum)

    refresh_flows(conn, rule_set, month, run_id)
    nxt = f"{int(month[:4]) + (month[5:] == '12')}-{(int(month[5:]) % 12) + 1:02d}"
    refresh_flows(conn, rule_set, nxt, run_id)              # the next month's Abgänge depend on this month
    from statagent.qa import checks, report   # after the numbers: findings and the QB read them
    say("checks", 80, "Qualitätsprüfungen laufen")
    findings = checks.run_checks(conn, run_id, month, rule_set, params, rules)
    say("report", 92, f"{len(findings)} Auffälligkeiten – Qualitätsbericht wird erstellt")
    path = report.write_quality_report(conn, run_id, month, rule_set, write_file=write_files and not preview)
    say("done", 100, f"Fertig: {metrics['records_total']:,} Verhältnisse, Prüfsumme {checksum[:8]}".replace(",", "."))
    return {"run_id": run_id, "month": month, "rule_set": rule_set, "rules": applied, "checksum": checksum,
            "metrics": metrics, "findings": len(findings), "report": path, "published": frozen == checksum}


def run(month: str, rule_set: str = "basis", preview: tuple[str, ...] = (), progress=None) -> dict:
    """CLI entry: one run in its own transaction (a preview is rolled back)."""
    log = setup_logging("lauf")
    with connect() as conn:
        try:
            with conn.transaction(force_rollback=bool(preview)):
                result = run_month(conn, month, rule_set, preview, log, progress)
        except RunError as exc:
            log.error(str(exc))
            with conn.transaction():
                conn.execute("""INSERT INTO ops.run (kind, delivery, rule_set, status, finished_at, note)
                                VALUES ('month', %s, %s, 'failed', now(), %s)""", (month, rule_set, str(exc)[:1000]))
            raise
    if preview:
        log.info("preview finished – rolled back, nothing stored")
    return result


def all_months(conn) -> list[str]:
    return [r[0] for r in conn.execute("SELECT lieferung FROM roh.ladeprotokoll ORDER BY lieferung").fetchall()]


def run_all(rule_set: str = "basis", progress=None) -> list[dict]:
    """Overall run = 24 single runs in chronological order (Fachbeschreibung §2a), each its own transaction."""
    with connect() as conn:
        months = all_months(conn)
    return [run(m, rule_set, progress=progress) for m in months]


def publish(person: str, rule_set: str = "basis", month: str | None = None, comment: str | None = None) -> list[str]:
    """Named approval of finished months (T7): status 'endgueltig', frozen from now on (Z4)."""
    from statagent.core.rules import valid_person
    person = valid_person(person)
    done = []
    with connect() as conn, conn.transaction():
        rows = conn.execute("""SELECT DISTINCT substr(stand, 11) FROM stat_beschaeftigte
                               WHERE regelwerk = %s AND status = 'vorlaeufig' AND (%s::text IS NULL OR stand = 'Lieferung ' || %s)
                               ORDER BY 1""", (rule_set, month, month)).fetchall()
        for (m,) in rows:
            run_id = conn.execute("SELECT max(lauf_id) FROM stat_beschaeftigte WHERE regelwerk = %s AND stand = %s",
                                  (rule_set, f"Lieferung {m}")).fetchone()[0]
            conn.execute("UPDATE stat_beschaeftigte SET status = 'endgueltig' WHERE regelwerk = %s AND stand = %s",
                         (rule_set, f"Lieferung {m}"))
            conn.execute("""INSERT INTO ops.approval (object_type, object_id, decision, person, comment)
                            VALUES ('month', %s, 'approved', %s, %s)""", (f"{rule_set}:{m}:run{run_id}", person, comment))
            conn.execute("""INSERT INTO ops.change_log (instruction, change, object, approved_by) VALUES (%s, %s, %s, %s)""",
                         (comment, f"Berichtsmonat {m} ({rule_set}) veröffentlicht, Lauf {run_id}", f"month:{rule_set}:{m}", person))
            done.append(m)
    from statagent.qa import report
    with connect() as conn, conn.transaction():
        for m in done:
            run_id = conn.execute("SELECT max(lauf_id) FROM stat_beschaeftigte WHERE regelwerk = %s AND stand = %s",
                                  (rule_set, f"Lieferung {m}")).fetchone()[0]
            report.write_quality_report(conn, run_id, m, rule_set)
    return done
