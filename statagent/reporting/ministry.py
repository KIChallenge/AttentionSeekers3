"""Change order 3 – delivery to the ministry: ministerium_JJJJ-MM.csv (aenderungsauftraege.md, Auftrag 3).

Parameters live in the approved rule with action 'ministry_delivery' (rule set 'auftraege', T3); this code implements
the action. Definition:
- persons with >= `min_days` calendar days as ArbeiterDV/ArbeiterFD in ÖNACE section C within the 12 months up to and
  including the reporting month (07/2026 → 01.08.2025–31.07.2026)
- a day counts once per person (simultaneous VVH, DV + FD added up), via range_agg over day ranges
- data basis (deviating from Z4): for every day the latest delivery that contains it, but never a later delivery than the
  reporting month → days of month X come from delivery min(X + 2 months, reporting month)
- the delivery's own ÖNACE version: section C via quellzuordnung_wirksam (incl. R-DQ07 DA–DM → C)
- processed with the approved reading rules (store.segment.effective_end: R-DQ01/09/10 if approved)
- `incomplete_deliveries` (DQ-02, e.g. 2025-10): a VVH missing completely from such a delivery keeps its segments
  from the previous delivery for the days that delivery covers (otherwise ~20 % of the VVH would lose those days)
- GEBURTSJAHR: year of the delivered date; `Unbekannt` for implausible dates (age > 110, DQ-06, or no readable year).
  Month 13 (DQ-05): only the month is invalid, the year is used (same assumption as R-DQ05); see the rule text.
- sorted by PERSON_ID (numerically), semicolon, header as vorlagen/ministerium_vorlage.csv
The file is a delivery: it needs a named approval (T7) before it is handed over (`lieferung-freigeben`).
"""
import datetime as dt
import hashlib

from statagent.config import BASE_DIR
from statagent.etl.store import month_bounds

OUT_DIR = BASE_DIR / "abgabe"
TEMPLATE = BASE_DIR / "vorlagen" / "ministerium_vorlage.csv"
DEFAULTS = {"report_month": "2026-07", "months": 12, "min_days": 200, "quals": ["ArbeiterDV", "ArbeiterFD"], "oenace": "C",
            "incomplete_deliveries": ["2025-10"], "max_age": 110}


def _add_months(month: str, n: int) -> str:
    y, m = map(int, month.split("-"))
    k = y * 12 + (m - 1) + n
    return f"{k // 12}-{k % 12 + 1:02d}"


def plan(report_month: str, n_months: int, available: list[str]) -> list[dict]:
    """Which delivery supplies the days of which month (latest delivery containing the day, ≤ reporting month)."""
    out = []
    for i in range(n_months - 1, -1, -1):
        month = _add_months(report_month, -i)
        source = min(_add_months(month, 2), report_month)
        if source not in available:
            raise ValueError(f"Lieferung {source} (für die Tage im {month}) ist nicht geladen")
        start, end = month_bounds(month)
        out.append({"month": month, "delivery": source, "start": start, "end": end})
    return out


SQL = """
WITH src AS (
  SELECT * FROM jsonb_to_recordset(%(plan)s::jsonb) AS x(month text, delivery text, start date, "end" date)
), seg AS (
  SELECT s.person_id, s.vvh_id, src.month, src.delivery AS used_delivery,
         daterange(greatest(s.begin_date, src.start), least(coalesce(s.effective_end, src."end"), src."end"), '[]') AS days
  FROM src JOIN store.segment s ON s.delivery = src.delivery AND s.counted
  JOIN quellzuordnung_wirksam q ON q.quelle = 'ZVD-Monatslieferung' AND q.merkmal = 'OENACE' AND q.quellwert = coalesce(s.oenace, '')
       AND src."end" BETWEEN q.gueltig_von AND coalesce(q.gueltig_bis, 'infinity') AND q.code = %(oenace)s
  WHERE s.qual = ANY(%(quals)s) AND s.begin_date <= src."end" AND (s.effective_end IS NULL OR s.effective_end >= src.start)
    AND (s.effective_end IS NULL OR s.effective_end >= s.begin_date)
  UNION ALL
  -- DQ-02: VVH missing completely from an incomplete delivery keep their segments from the previous delivery
  SELECT p.person_id, p.vvh_id, src.month, p.delivery,
         daterange(greatest(p.begin_date, src.start), least(coalesce(p.effective_end, src."end"), src."end"), '[]')
  FROM src JOIN store.segment p ON p.delivery = to_char(to_date(src.delivery, 'YYYY-MM') - interval '1 month', 'YYYY-MM') AND p.counted
  JOIN quellzuordnung_wirksam q ON q.quelle = 'ZVD-Monatslieferung' AND q.merkmal = 'OENACE' AND q.quellwert = coalesce(p.oenace, '')
       AND src."end" BETWEEN q.gueltig_von AND coalesce(q.gueltig_bis, 'infinity') AND q.code = %(oenace)s
  WHERE src.delivery = ANY(%(incomplete)s) AND p.qual = ANY(%(quals)s)
    AND p.begin_date <= src."end" AND (p.effective_end IS NULL OR p.effective_end >= src.start)
    AND (p.effective_end IS NULL OR p.effective_end >= p.begin_date)
    AND src."end" <= (to_date(src.delivery, 'YYYY-MM') - interval '1 day')::date   -- only days the previous delivery covers
    AND NOT EXISTS (SELECT 1 FROM store.segment c WHERE c.delivery = src.delivery AND c.vvh_id = p.vvh_id)
), per_person AS (
  SELECT person_id, range_agg(days) AS days FROM seg WHERE NOT isempty(days) GROUP BY person_id
), counted AS (
  SELECT person_id, (SELECT sum(upper(r) - lower(r)) FROM unnest(days) r)::int AS tage FROM per_person
), attrs AS (
  -- sex and birth date from the newest delivery used for the person (stable per VVH, Problems.md §4.1)
  SELECT DISTINCT ON (x.person_id) x.person_id, s.sex, s.birth_date_raw
  FROM seg x JOIN store.segment s ON s.delivery = x.used_delivery AND s.vvh_id = x.vvh_id
  ORDER BY x.person_id, x.used_delivery DESC, x.vvh_id
)
SELECT c.person_id, c.tage, a.sex, a.birth_date_raw, NULL
FROM counted c JOIN attrs a USING (person_id) WHERE c.tage >= %(min_days)s
"""


def birth_year(raw: str | None, ref: dt.date, max_age: int) -> str:
    if not raw or len(raw) < 4 or not raw[:4].isdigit():
        return "Unbekannt"
    year = int(raw[:4])
    if ref.year - year > max_age or year > ref.year:
        return "Unbekannt"   # DQ-06: implausible birth date
    return str(year)          # also for month 13 (DQ-05): the year is plausible


def build(conn, params: dict | None = None, out_dir=None) -> dict:
    p = {**DEFAULTS, **(params or {})}
    available = [r[0] for r in conn.execute("SELECT lieferung FROM roh.ladeprotokoll ORDER BY 1").fetchall()]
    days_plan = plan(p["report_month"], int(p["months"]), available)
    _, ref = month_bounds(p["report_month"])
    import json
    rows = conn.execute(SQL, {"plan": json.dumps([{**d, "start": d["start"].isoformat(), "end": d["end"].isoformat()} for d in days_plan]),
                              "oenace": p["oenace"], "quals": p["quals"], "incomplete": p["incomplete_deliveries"],
                              "report_month": p["report_month"], "min_days": int(p["min_days"])}).fetchall()
    out_rows = []
    for person, tage, sex, bd, _ in rows:
        out_rows.append((person, sex or "Unbekannt", birth_year(bd, ref, int(p["max_age"])), int(tage)))
    out_rows.sort(key=lambda r: (len(r[0]), r[0]))
    header = TEMPLATE.read_text(encoding="utf-8").strip().splitlines()[0]
    text = header + "\n" + "".join(f"{a};{b};{c};{d}\n" for a, b, c, d in out_rows)
    target = (out_dir or OUT_DIR) / f"ministerium_{p['report_month']}.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(text.encode("utf-8"))
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    dupes = len(out_rows) - len({r[0] for r in out_rows})
    stats = {"persons": len(out_rows), "duplicates": dupes, "unknown_birth_year": sum(r[2] == "Unbekannt" for r in out_rows),
             "min_days_found": min((r[3] for r in out_rows), default=None), "max_days_found": max((r[3] for r in out_rows), default=None),
             "sorted": out_rows == sorted(out_rows, key=lambda r: (len(r[0]), r[0]))}
    try:
        rel = target.relative_to(BASE_DIR).as_posix()
    except ValueError:
        rel = str(target)
    conn.execute("INSERT INTO ops.report (kind, rule_set, month, path, sha256) VALUES ('ministry', 'auftraege', %s, %s, %s)",
                 (p["report_month"], rel, digest))
    return {"path": rel, "sha256": digest, "params": p, "plan": [{**d, "start": d["start"].isoformat(), "end": d["end"].isoformat()}
                                                                for d in days_plan], **stats}
