"""Versioned store store.segment: every delivered record per delivery, typed and flagged.

- Raw values stay next to the interpreted ones; roh.lieferung is only read.
- Problem flags (column `problems`) are detected independently of any rule.
- Reading rules change the *interpretation* only and are applied only once approved
  (ops.rule.status = 'approved'). Implemented actions:
    swap_columns           R-DQ01  read BEGINN/ENDE swapped for the listed deliveries
    count_duplicates_once  R-DQ03  exact duplicate rows count once
    trim_overlap           R-DQ09  overlapping/open segment ends the day before the next one
    close_gap              R-DQ10  segment before a gap lasts until the day before the next one
- Each delivery is built from its own rows only, so no later delivery leaks into a month.
- Every build is a run in ops.run with the applied rules and a checksum (T1).
"""
import calendar
import datetime as dt
from concurrent.futures import ThreadPoolExecutor

from statagent.config import connect, setup_logging

ACTIONS = ("swap_columns", "count_duplicates_once", "trim_overlap", "close_gap")

INSERT_SQL = """
INSERT INTO store.segment (delivery, vvh_id, person_id, birth_date_raw, sex, begin_raw, end_raw,
  qual, oenace, bundesland, copy_no, birth_date, birth_year, begin_date, end_date, effective_end, counted,
  problems, rules, run_id)
WITH typed AS (
  SELECT r.*,
         store.iso_date(r.geburtsdatum) AS bd,
         CASE WHEN r.geburtsdatum ~ '^\\d{4}-' THEN substr(r.geburtsdatum, 1, 4)::int END AS by,
         store.iso_date(r.beginn) AS begin_d,
         store.iso_date(r.ende) AS end_d
  FROM roh.lieferung r
  WHERE r.lieferung = %(delivery)s
), base AS (
  SELECT *,
         row_number() OVER (PARTITION BY vvh_id, person_id, geburtsdatum, geschlecht, beginn, ende,
                                         qual, oenace, bundesland ORDER BY vvh_id) AS copy_no,
         CASE WHEN %(r_swap)s::text IS NOT NULL THEN end_d ELSE begin_d END AS b,
         CASE WHEN %(r_swap)s::text IS NOT NULL THEN begin_d ELSE end_d END AS e
  FROM typed
), with_count AS (
  SELECT *, NOT (copy_no > 1 AND %(r_dq03)s::text IS NOT NULL) AS counted FROM base
), segment AS (
  SELECT *, CASE WHEN counted AND b IS NOT NULL THEN
              lead(b) OVER (PARTITION BY vvh_id, (counted AND b IS NOT NULL)
                            ORDER BY b, e NULLS LAST, qual, oenace, bundesland, copy_no) END AS nb
  FROM with_count
), effective AS (
  SELECT *,
         CASE WHEN nb IS NULL THEN NULL
              WHEN e IS NULL THEN 'DQ-11'
              WHEN nb <= e THEN 'DQ-09'
              WHEN nb > e + 1 THEN 'DQ-10' END AS seg_problem,
         CASE WHEN nb IS NOT NULL AND (e IS NULL OR nb <= e) THEN %(r_dq09)s::text
              WHEN nb IS NOT NULL AND nb > e + 1 THEN %(r_dq10)s::text END AS seg_rule
  FROM segment
), reference_day AS (
  SELECT *, counted AND b <= %(reference_date)s AND (ew IS NULL OR ew >= %(reference_date)s) AS on_reference_date
  FROM (SELECT *, CASE WHEN seg_rule IS NOT NULL THEN nb - 1 ELSE e END AS ew FROM effective) w
), doubled AS (
  -- DQ-16: new VVH in the reporting month while the same person already has an older VVH with identical
  -- QUAL/OENACE/BUNDESLAND active on the Stichtag (suspected double registration; own delivery only).
  SELECT *, on_reference_date AND b >= %(month_start)s
            AND first_value(vvh_id) OVER g <> vvh_id AND first_value(b) OVER g < b AS dq16
  FROM reference_day
  WINDOW g AS (PARTITION BY person_id, qual, oenace, bundesland, on_reference_date ORDER BY b, vvh_id)
)
SELECT lieferung, vvh_id, person_id, geburtsdatum, geschlecht, beginn, ende, qual, oenace, bundesland,
       copy_no, bd, by, b, e, ew, counted,
       array_remove(ARRAY[
         CASE WHEN (beginn IS NULL AND ende IS NOT NULL) OR end_d < begin_d THEN 'DQ-01' END,
         CASE WHEN copy_no > 1 THEN 'DQ-03' END,
         CASE WHEN geburtsdatum IS NOT NULL AND bd IS NULL THEN 'DQ-05' END,
         CASE WHEN coalesce(bd <= %(reference_date)s::date - interval '111 years', by <= %(year)s - 111) THEN 'DQ-06' END,
         CASE WHEN oenace ~ '^D[A-N]$' THEN 'DQ-07' END,
         CASE WHEN oenace IS NULL OR bundesland IS NULL THEN 'DQ-08' END,
         seg_problem,
         CASE WHEN dq16 THEN 'DQ-16' END,
         CASE WHEN bd IS NOT NULL AND b < bd + interval '15 years' THEN 'DQ-17' END
       ], NULL),
       array_remove(ARRAY[
         %(r_swap)s::text,
         CASE WHEN copy_no > 1 THEN %(r_dq03)s::text END,
         seg_rule
       ], NULL),
       %(run_id)s
FROM doubled
"""

PROFILE_SQL = """
SELECT
  count(*) AS row_count,
  count(DISTINCT vvh_id) FILTER (WHERE counted AND begin_date <= %(reference_date)s
                                   AND (effective_end IS NULL OR effective_end >= %(reference_date)s)) AS active,
  count(DISTINCT vvh_id) FILTER (WHERE store.iso_date(begin_raw) <= %(reference_date)s
                                   AND (end_raw IS NULL OR store.iso_date(end_raw) >= %(reference_date)s)) AS active_as_delivered,
  count(*) FILTER (WHERE 'DQ-01' = ANY(problems)) AS dq01_rows,
  count(*) FILTER (WHERE 'DQ-03' = ANY(problems)) AS dq03_copies,
  count(*) FILTER (WHERE 'DQ-05' = ANY(problems)) AS dq05_rows,
  count(*) FILTER (WHERE 'DQ-06' = ANY(problems)) AS dq06_rows,
  count(*) FILTER (WHERE 'DQ-07' = ANY(problems)) AS dq07_rows,
  count(*) FILTER (WHERE 'DQ-08' = ANY(problems)) AS dq08_rows,
  count(DISTINCT vvh_id) FILTER (WHERE 'DQ-09' = ANY(problems)) AS dq09_vvh,
  count(DISTINCT vvh_id) FILTER (WHERE 'DQ-10' = ANY(problems)) AS dq10_vvh,
  count(DISTINCT vvh_id) FILTER (WHERE 'DQ-11' = ANY(problems)) AS dq11_vvh,
  count(DISTINCT vvh_id) FILTER (WHERE 'DQ-16' = ANY(problems)) AS dq16_vvh,
  count(*) FILTER (WHERE 'DQ-17' = ANY(problems)) AS dq17_rows,
  count(*) FILTER (WHERE qual LIKE '%%FD') AS fd_rows,
  count(*) FILTER (WHERE cardinality(rules) > 0) AS rows_with_rule
FROM store.segment WHERE delivery = %(delivery)s
"""

CHECKSUM_SQL = """
SELECT md5(string_agg(md5(ROW(vvh_id, person_id, birth_date_raw, sex, begin_raw, end_raw, qual, oenace,
                              bundesland, copy_no, birth_date, birth_year, begin_date, end_date, effective_end, counted,
                              problems, rules)::text), ''
                  ORDER BY vvh_id, begin_raw, end_raw, copy_no, qual, oenace, bundesland, person_id,
                           birth_date_raw, sex))
FROM store.segment WHERE delivery = %(delivery)s
"""


def month_bounds(delivery: str) -> tuple[dt.date, dt.date]:
    """First day and last day (Stichtag) of the reporting month JJJJ-MM."""
    year, month = map(int, delivery.split("-"))
    return dt.date(year, month, 1), dt.date(year, month, calendar.monthrange(year, month)[1])


def approved_rules(conn, extra: tuple[str, ...] = ()) -> list[dict]:
    """Approved reading rules (plus `extra` rule IDs for a preview) with an implemented action."""
    cur = conn.execute("""SELECT rule_id, action, parameters FROM ops.rule
                          WHERE rule_set = 'basis' AND action = ANY(%s)
                            AND (status = 'approved' OR rule_id = ANY(%s)) ORDER BY rule_id""",
                       (list(ACTIONS), list(extra)))
    return [dict(zip(("rule_id", "action", "parameters"), r)) for r in cur.fetchall()]


def rule_params(rules: list[dict], delivery: str) -> dict:
    """SQL parameters: the rule ID per action (NULL = not applied for this delivery)."""
    by_action = {r["action"]: r for r in rules}
    swap = by_action.get("swap_columns")
    return {
        "r_swap": swap["rule_id"] if swap and delivery in swap["parameters"].get("deliveries", []) else None,
        "r_dq03": by_action.get("count_duplicates_once", {}).get("rule_id"),
        "r_dq09": by_action.get("trim_overlap", {}).get("rule_id"),
        "r_dq10": by_action.get("close_gap", {}).get("rule_id"),
    }


def build_delivery(conn, delivery: str, rules: list[dict], run_id: int) -> tuple[dict, str]:
    """Rebuild one delivery in the store; returns (profile, checksum)."""
    month_start, reference_date = month_bounds(delivery)
    params = {"delivery": delivery, "month_start": month_start, "reference_date": reference_date,
              "year": reference_date.year, "run_id": run_id, **rule_params(rules, delivery)}
    conn.execute("DELETE FROM store.segment WHERE delivery = %(delivery)s", params)
    conn.execute(INSERT_SQL, params)
    cur = conn.execute(PROFILE_SQL, params)
    profile = dict(zip([c.name for c in cur.description], cur.fetchone()))
    conn.execute("DELETE FROM store.profile WHERE delivery = %s", (delivery,))
    for key, value in profile.items():
        conn.execute("INSERT INTO store.profile VALUES (%s, %s, %s, %s)", (delivery, key, value, run_id))
    checksum = conn.execute(CHECKSUM_SQL, params).fetchone()[0]
    return profile, checksum


def deliveries(conn, only: str | None = None) -> list[str]:
    rows = conn.execute("SELECT lieferung FROM roh.ladeprotokoll ORDER BY lieferung").fetchall()
    selected = [r[0] for r in rows if only is None or r[0] == only]
    if only and not selected:
        raise ValueError(f"Lieferung {only} ist nicht geladen")
    return selected


INDEXES = {"segment_delivery_vvh": "(delivery, vvh_id)", "segment_delivery_person": "(delivery, person_id)",
           "segment_vvh_delivery": "(vvh_id, delivery)"}


def _start_run(conn, delivery, applied, note) -> int:
    return conn.execute("""INSERT INTO ops.run (kind, delivery, rules, note) VALUES ('store', %s, %s, %s)
                           RETURNING run_id""", (delivery, applied, note)).fetchone()[0]


def _finish_run(conn, run_id, profiles, checksums) -> None:
    total = sum(p["row_count"] for p in profiles.values())
    conn.execute("""UPDATE ops.run SET status = 'done', finished_at = now(), row_count = %s, checksum = md5(%s)
                    WHERE run_id = %s""", (total, "".join(checksums[m] for m in sorted(checksums)), run_id))


def _log_delivery(log, month, p) -> None:
    log.info("  %s: %s rows, active at Stichtag %s (as delivered %s)", month, f"{p['row_count']:,}",
             f"{p['active']:,}", f"{p['active_as_delivered']:,}")


def build_store(delivery: str | None = None, preview: tuple[str, ...] = (), workers: int = 6) -> dict[str, dict]:
    """Build the store with all approved reading rules.

    - one delivery or a preview: one transaction (a preview applies the given proposed rules in
      addition and is rolled back, nothing is stored)
    - all deliveries: table emptied, deliveries built in parallel (each in its own transaction,
      each from its own rows only), indexes rebuilt once at the end
    """
    log = setup_logging("bestand")
    profiles, checksums = {}, {}
    if delivery or preview:
        with connect() as conn, conn.transaction(force_rollback=bool(preview)):
            rules = approved_rules(conn, preview)
            run_id = _start_run(conn, delivery, [r["rule_id"] for r in rules],
                                f"Vorschau mit {', '.join(preview)}" if preview else None)
            log.info("%sstore build, run %s, rules applied: %s", "PREVIEW " if preview else "", run_id,
                     [r["rule_id"] for r in rules] or "none")
            for month in deliveries(conn, delivery):
                profiles[month], checksums[month] = build_delivery(conn, month, rules, run_id)
                _log_delivery(log, month, profiles[month])
                log.info("  checksum %s: %s", month, checksums[month])
            _finish_run(conn, run_id, profiles, checksums)
        log.info("preview finished – rolled back, nothing stored" if preview else "done")
        return profiles

    with connect(autocommit=True) as conn:
        rules = approved_rules(conn)
        run_id = _start_run(conn, None, [r["rule_id"] for r in rules], None)
        months = deliveries(conn)
        log.info("store build (all deliveries, %s workers), run %s, rules applied: %s", workers, run_id,
                 [r["rule_id"] for r in rules] or "none")
        conn.execute("TRUNCATE store.segment, store.profile")
        conn.execute("DROP INDEX IF EXISTS " + ", ".join(f"store.{name}" for name in INDEXES))

        def build(month):
            with connect() as worker, worker.transaction():
                return month, *build_delivery(worker, month, rules, run_id)

        try:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for month, profile, checksum in pool.map(build, months):
                    profiles[month], checksums[month] = profile, checksum
                    _log_delivery(log, month, profile)
        except Exception:
            conn.execute("UPDATE ops.run SET status = 'failed', finished_at = now() WHERE run_id = %s", (run_id,))
            raise
        for name, columns in INDEXES.items():
            conn.execute(f"CREATE INDEX IF NOT EXISTS {name} ON store.segment {columns}")
        conn.execute("ANALYZE store.segment")
        _finish_run(conn, run_id, profiles, checksums)
        log.info("done: %s rows in %s deliveries", f"{sum(p['row_count'] for p in profiles.values()):,}", len(profiles))
    return dict(sorted(profiles.items()))


def stored_profile(conn) -> dict[str, dict]:
    profiles: dict[str, dict] = {}
    for delivery, metric, value in conn.execute("SELECT delivery, metric, value FROM store.profile ORDER BY delivery"):
        profiles.setdefault(delivery, {})[metric] = int(value)
    return profiles


# German column headers: the profile table is shown to users.
COLUMNS = [("row_count", "Zeilen"), ("active", "Aktiv"), ("active_as_delivered", "Aktiv wie geliefert"), ("dq03_copies", "Dubletten"),
           ("dq05_rows", "Monat 13"), ("dq06_rows", "Alter > 110"), ("dq07_rows", "ÖNACE 2003"),
           ("dq08_rows", "Ohne ÖNACE/BL"), ("dq09_vvh", "Überl."), ("dq10_vvh", "Lücken"), ("dq11_vvh", "Offen+Folge"),
           ("dq17_rows", "Beginn < 15"), ("dq16_vvh", "DQ-16 Verdacht"), ("fd_rows", "FD-Sätze"), ("dq01_rows", "DQ-01-Sätze")]


def profile_table(profiles: dict[str, dict]) -> str:
    """Markdown table (German) of the profile incl. delivery-level checks (DQ-02 drop, DQ-04 no FD)."""
    lines = ["| Lieferung | " + " | ".join(h for _, h in COLUMNS) + " | Prüfungen |",
             "| --- |" + " ---: |" * len(COLUMNS) + " --- |"]
    previous = None
    for month, p in profiles.items():
        checks = []
        if previous and previous["active"] and p["active"] < 0.9 * previous["active"]:
            checks.append(f"DQ-02? aktiv {p['active'] / previous['active'] - 1:+.0%} gegenüber Vormonat")
        if previous and previous["fd_rows"] and p["fd_rows"] == 0:
            checks.append("DQ-04? keine FD")
        if p["dq01_rows"] > 0.5 * p["row_count"]:
            checks.append("DQ-01? BEGINN/ENDE unplausibel")
        lines.append(f"| {month} | " + " | ".join(f"{p[k]:,}" for k, _ in COLUMNS) + f" | {'; '.join(checks)} |")
        previous = p
    return "\n".join(lines)
