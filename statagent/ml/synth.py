"""Synthetic delivery generator (Phase 3b, PRD §5.2) – seeded micro-simulation of VVH lifecycles.

Calibration (deterministic SQL on the real production results, rule set 'basis'):
  - start and end rates per ÖNACE section letter and calendar month (Zu-/Abgänge ÷ Vormonatsbestand), months affected by
    DQ-02/DQ-04 and the ÖNACE break (01/2025) left out
  - multipliers per Qualifikation (e.g. Beamte: hardly any starts → the real decline, RD-02)
  - joint distribution of (section, Bundesland, Qualifikation, Geschlecht, Geburtsjahr) from 08/2024
  - background problem rates seen in every real delivery (month 13, age > 110, ÖNACE 2003 codes, empty codes, phantom
    double registrations, late end reports)
Simulation: `scale` VVH (default 1:20 of the real stock), monthly; every month a delivery with all segments of the last three
months in the delivered column layout. Planted, labelled errors (synth.label): DQ-01 swapped columns, DQ-02 incomplete delivery,
DQ-03 exact duplicates, DQ-04 missing freie Dienstverträge – random month and intensity per run.
Reproducible: same seed and calibration → same checksum. Synthetic data never enters stat_* or store.*.
"""
import datetime as dt
import hashlib
import json

import numpy as np
import pandas as pd

COLUMNS = ["vvh_id", "person_id", "geburtsdatum", "geschlecht", "beginn", "ende", "qual", "oenace", "bundesland"]
PLANTED = ("DQ-01", "DQ-02", "DQ-03", "DQ-04")
START = dt.date(2024, 8, 1)
EXCLUDED_MONTHS = ("2025-01", "2025-03", "2025-04", "2025-10", "2025-11")


def _month_add(d: dt.date, n: int) -> dt.date:
    k = d.year * 12 + d.month - 1 + n
    return dt.date(k // 12, k % 12 + 1, 1)


def _month_end(d: dt.date) -> dt.date:
    return _month_add(d, 1) - dt.timedelta(days=1)


def calibrate(conn) -> dict:
    """Rates and distributions from the real results (only numbers produced by the deterministic runs)."""
    flows = conn.execute("""
        WITH m AS (SELECT DISTINCT month FROM store.month_record WHERE rule_set = 'basis'),
        pairs AS (SELECT to_char(to_date(month, 'YYYY-MM') - interval '1 month', 'YYYY-MM') AS prev, month AS cur FROM m
                  WHERE month <> ALL(%s) AND to_char(to_date(month, 'YYYY-MM') - interval '1 month', 'YYYY-MM') IN (SELECT month FROM m))
        SELECT p.cur, left(o.oenace, 1) AS sec, o.qualifikation, count(*) AS stock,
               count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM store.month_record c WHERE c.rule_set = 'basis' AND c.month = p.cur
                                                  AND c.vvh_id = o.vvh_id)) AS ends
        FROM pairs p JOIN store.month_record o ON o.rule_set = 'basis' AND o.month = p.prev
        GROUP BY 1, 2, 3""", (list(EXCLUDED_MONTHS),)).fetchall()
    starts = conn.execute("""
        WITH m AS (SELECT DISTINCT month FROM store.month_record WHERE rule_set = 'basis')
        SELECT c.month, left(c.oenace, 1), c.qualifikation, count(*)
        FROM store.month_record c WHERE c.rule_set = 'basis' AND c.month <> ALL(%s)
          AND to_char(to_date(c.month, 'YYYY-MM') - interval '1 month', 'YYYY-MM') IN (SELECT month FROM m)
          AND NOT EXISTS (SELECT 1 FROM store.month_record o WHERE o.rule_set = 'basis'
                          AND o.month = to_char(to_date(c.month, 'YYYY-MM') - interval '1 month', 'YYYY-MM') AND o.vvh_id = c.vvh_id)
          AND NOT ('DQ-16' = ANY(c.problems))
        GROUP BY 1, 2, 3""", (list(EXCLUDED_MONTHS),)).fetchall()
    seasonal = "o.region IN ('2', '5', '7', '8') AND left(o.oenace, 1) IN ('A', 'F', 'I', 'N', 'R', 'S')"
    ends_bl = conn.execute(f"""
        WITH m AS (SELECT DISTINCT month FROM store.month_record WHERE rule_set = 'basis'),
        pairs AS (SELECT to_char(to_date(month, 'YYYY-MM') - interval '1 month', 'YYYY-MM') AS prev, month AS cur FROM m
                  WHERE month <> ALL(%s) AND to_char(to_date(month, 'YYYY-MM') - interval '1 month', 'YYYY-MM') IN (SELECT month FROM m))
        SELECT extract(month FROM to_date(p.cur, 'YYYY-MM'))::int AS cal, left(o.oenace, 1) AS sec, o.region AS bl, count(*) AS stock,
               count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM store.month_record c WHERE c.rule_set = 'basis' AND c.month = p.cur
                                                  AND c.vvh_id = o.vvh_id)) AS ends
        FROM pairs p JOIN store.month_record o ON o.rule_set = 'basis' AND o.month = p.prev
        WHERE {seasonal} GROUP BY 1, 2, 3""", (list(EXCLUDED_MONTHS),)).fetchall()
    starts_bl = conn.execute(f"""
        WITH m AS (SELECT DISTINCT month FROM store.month_record WHERE rule_set = 'basis')
        SELECT extract(month FROM to_date(o.month, 'YYYY-MM'))::int AS cal, left(o.oenace, 1) AS sec, o.region AS bl, count(*) AS starts
        FROM store.month_record o WHERE o.rule_set = 'basis' AND o.month <> ALL(%s) AND {seasonal}
          AND to_char(to_date(o.month, 'YYYY-MM') - interval '1 month', 'YYYY-MM') IN (SELECT month FROM m)
          AND NOT ('DQ-16' = ANY(o.problems))
          AND NOT EXISTS (SELECT 1 FROM store.month_record x WHERE x.rule_set = 'basis'
                          AND x.month = to_char(to_date(o.month, 'YYYY-MM') - interval '1 month', 'YYYY-MM') AND x.vvh_id = o.vvh_id)
        GROUP BY 1, 2, 3""", (list(EXCLUDED_MONTHS),)).fetchall()
    f = pd.DataFrame(flows, columns=["month", "sec", "qual", "stock", "ends"])
    s = pd.DataFrame(starts, columns=["month", "sec", "qual", "starts"])
    fb = pd.DataFrame(ends_bl, columns=["cal", "sec", "bl", "stock", "ends"]).set_index(["cal", "sec", "bl"]).join(
        pd.DataFrame(starts_bl, columns=["cal", "sec", "bl", "starts"]).set_index(["cal", "sec", "bl"]), how="left").fillna(0)
    fb = fb[fb["stock"] >= 150]
    f["cal"], s["cal"] = f["month"].str[5:].astype(int), s["month"].str[5:].astype(int)
    stock_sec = f.groupby(["cal", "sec"])["stock"].sum()
    end_rate = (f.groupby(["cal", "sec"])["ends"].sum() / stock_sec).fillna(0)
    start_rate = (s.groupby(["cal", "sec"])["starts"].sum() / stock_sec).fillna(0)
    # the national rate of a section also contains the regions with own rates: use the rate of the *other* regions as fallback
    tot = pd.DataFrame({"stock": f.groupby(["cal", "sec"])["stock"].sum(), "ends": f.groupby(["cal", "sec"])["ends"].sum()}).join(
        s.groupby(["cal", "sec"])["starts"].sum(), how="left").fillna(0)
    own = fb.groupby(level=["cal", "sec"])[["stock", "ends", "starts"]].sum()
    rest = tot.join(own, rsuffix="_own", how="left").fillna(0)
    rest_ok = (rest["stock"] - rest["stock_own"]) >= 150
    rest_end = ((rest["ends"] - rest["ends_own"]) / (rest["stock"] - rest["stock_own"]))[rest_ok]
    rest_start = ((rest["starts"] - rest["starts_own"]) / (rest["stock"] - rest["stock_own"]))[rest_ok]
    end_rate = rest_end.combine_first(end_rate)
    start_rate = rest_start.combine_first(start_rate)
    # year-to-year variability of the seasonal rates (same calendar month in the two real years), per section
    per_month = f.groupby(["month", "sec"])[["ends", "stock"]].sum()
    per_month["r"] = np.log((per_month["ends"] + 1) / per_month["stock"])
    per_month = per_month.reset_index()
    per_month["cal"] = per_month["month"].str[5:].astype(int)
    disp = per_month.groupby(["cal", "sec"])["r"].agg(lambda x: float(np.std(x, ddof=1)) if len(x) > 1 else np.nan)
    rate_sd = disp.groupby(level="sec").median().fillna(disp.median()).clip(0.02, 0.5)
    q_end = f.groupby("qual")["ends"].sum() / f.groupby("qual")["stock"].sum()
    q_start = s.groupby("qual")["starts"].sum() / f.groupby("qual")["stock"].sum()
    overall_end, overall_start = f["ends"].sum() / f["stock"].sum(), s["starts"].sum() / f["stock"].sum()
    pop = conn.execute("""SELECT left(oenace, 1), region, qualifikation, geschlecht, alter, count(*) FROM store.month_record
                          WHERE rule_set = 'basis' AND month = '2024-08' GROUP BY 1, 2, 3, 4, 5""").fetchall()
    background = conn.execute("""SELECT avg(value) FILTER (WHERE metric = 'dq05_rows') / avg(value) FILTER (WHERE metric = 'row_count'),
                                        avg(value) FILTER (WHERE metric = 'dq06_rows') / avg(value) FILTER (WHERE metric = 'row_count'),
                                        avg(value) FILTER (WHERE metric = 'dq07_rows') / avg(value) FILTER (WHERE metric = 'row_count'),
                                        avg(value) FILTER (WHERE metric = 'dq08_rows') / avg(value) FILTER (WHERE metric = 'row_count'),
                                        avg(value) FILTER (WHERE metric = 'dq16_vvh') / avg(value) FILTER (WHERE metric = 'active')
                                 FROM store.profile WHERE delivery <> ALL(%s)""", (["2025-03", "2025-06", "2025-10"],)).fetchone()
    late = conn.execute("""SELECT avg(new_vvh + vanished_vvh - vanished_dq16)::float / avg(published) FROM ops.revision
                           WHERE rule_set = 'basis' AND month <> ALL(%s) AND delivery <> ALL(%s)""",
                        (list(EXCLUDED_MONTHS), list(EXCLUDED_MONTHS))).fetchone()[0] or 0.002
    cal = {
        "end_rate_bl": {f"{c}|{k}|{b}": float(r.ends / r.stock) for (c, k, b), r in fb.iterrows()},
        "start_rate_bl": {f"{c}|{k}|{b}": float(r.starts / r.stock) for (c, k, b), r in fb.iterrows()},
        "rate_sd": {k: float(v) for k, v in rate_sd.items()},
        "end_rate": {f"{c}|{k}": float(v) for (c, k), v in end_rate.items()},
        "start_rate": {f"{c}|{k}": float(v) for (c, k), v in start_rate.items()},
        "q_end_mult": {q: float(v / overall_end) for q, v in q_end.items() if overall_end},
        "q_start_mult": {q: float(v / overall_start) for q, v in q_start.items() if overall_start},
        "population": [[a, b, c, d, e, int(n)] for a, b, c, d, e, n in pop],
        "background": dict(zip(("month13", "age110", "oenace2003", "empty", "phantom"), [float(x or 0) for x in background])),
        "late_report": float(late),
    }
    cal["hash"] = hashlib.sha256(json.dumps(cal, sort_keys=True).encode()).hexdigest()
    return cal


def simulate(cal: dict, seed: int, months: int = 36, scale: float = 0.05, plant: bool = True) -> tuple[list[pd.DataFrame], list[dict]]:
    """Returns (deliveries, labels). Delivery i covers months i-2 … i; labels: {delivery, problem_id, intensity}."""
    rng = np.random.default_rng(seed)
    pop = cal["population"]
    weights = np.array([p[5] for p in pop], dtype=float)
    n0 = int(weights.sum() * scale)
    cells = rng.choice(len(pop), size=n0, p=weights / weights.sum())
    origin = START.toordinal()

    sec = np.array([pop[c][0] for c in cells], dtype=object)
    region = np.array([pop[c][1] for c in cells], dtype=object)
    qual = np.array([pop[c][2] for c in cells], dtype=object)
    sex = np.array([pop[c][3] for c in cells], dtype=object)
    ages = np.array([int(pop[c][4]) if str(pop[c][4]).isdigit() else 40 for c in cells])
    birth = np.array([dt.date(2024 - a, 1, 1).toordinal() + int(rng.integers(0, 365)) for a in ages])
    begin = origin - rng.integers(30, 7000, size=n0)
    end = np.full(n0, np.iinfo(np.int64).max)
    next_id = n0
    # month loop: ends and starts by section/calendar month and qualification
    month_starts = [_month_add(START, i) for i in range(months)]
    for i, ms in enumerate(month_starts[1:], start=1):
        me = _month_end(ms)
        cal_m = ms.month
        active = end >= ms.toordinal()
        idx = np.where(active & (begin <= me.toordinal()))[0]
        qm = np.array([cal["q_end_mult"].get(q, 1.0) for q in qual[idx]])
        sec_idx = sec[idx]
        norm_ = {s_code: qm[sec_idx == s_code].mean() for s_code in np.unique(sec_idx)}   # section rates already contain the mix
        bl_idx = region[idx]
        # this month's rates vary around the calibrated seasonal rates like the two real years do (per section)
        shock_end = {s_code: float(np.exp(rng.normal(0, cal["rate_sd"].get(s_code, 0.1)))) for s_code in sorted(set(sec_idx))}
        shock_start = {s_code: float(np.exp(rng.normal(0, cal["rate_sd"].get(s_code, 0.1)))) for s_code in sorted(set(sec_idx))}
        er = np.array([cal["end_rate_bl"].get(f"{cal_m}|{s}|{b}", cal["end_rate"].get(f"{cal_m}|{s}", 0.01)) * shock_end[s]
                       for s, b in zip(sec_idx, bl_idx)]) * qm / np.array([norm_[s] for s in sec_idx])
        er = np.clip(er, 0, 0.95)
        ending = idx[rng.random(len(idx)) < er]
        end[ending] = ms.toordinal() + rng.integers(0, (me - ms).days, size=len(ending))   # ends before the Stichtag of the month
        # starts: proportional to the section stock, attributes copied from a random active VVH of the same section
        new_rows = []
        groups = {}
        for i_, (s_code, b_code) in enumerate(zip(sec[idx], region[idx])):
            key = (s_code, b_code) if f"{cal_m}|{s_code}|{b_code}" in cal["start_rate_bl"] else (s_code, None)
            groups.setdefault(key, []).append(idx[i_])
        for (s_code, b_code), members in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1] or "")):
            pool = np.array(members)
            rate = cal["start_rate_bl"][f"{cal_m}|{s_code}|{b_code}"] if b_code else cal["start_rate"].get(f"{cal_m}|{s_code}", 0.01)
            k = int(rng.poisson(len(pool) * rate * shock_start.get(s_code, 1.0)))
            if k == 0:
                continue
            w = np.array([max(cal["q_start_mult"].get(q, 1.0), 1e-6) for q in qual[pool]])   # e.g. Beamte: hardly any starts
            donors = rng.choice(pool, size=k, p=w / w.sum())
            new_rows.append(donors)
        if new_rows:
            donors = np.concatenate(new_rows)
            k = len(donors)
            sec, region, qual, sex = (np.concatenate([a, a[donors]]) for a in (sec, region, qual, sex))
            birth = np.concatenate([birth, birth[donors] + rng.integers(-3000, 3000, size=k)])
            begin = np.concatenate([begin, ms.toordinal() + rng.integers(0, (me - ms).days + 1, size=k)])
            end = np.concatenate([end, np.full(k, np.iinfo(np.int64).max)])
            next_id += k
    ids = np.arange(1, len(begin) + 1)
    person = ids + 1_000_000
    bg = cal["background"]
    # constant data properties seen in every real delivery
    m13 = rng.random(len(ids)) < bg["month13"]
    old = rng.random(len(ids)) < bg["age110"]
    o2003 = (rng.random(len(ids)) < bg["oenace2003"]) & (sec == "C")
    empty = rng.random(len(ids)) < bg["empty"]

    def fmt_date(o):
        return dt.date.fromordinal(int(o)).isoformat()

    births = [fmt_date(b) for b in birth]
    births = [("1850" + b[4:]) if o else (b[:5] + "13" + b[7:] if m and int(b[8:10]) <= 28 else b) for b, m, o in zip(births, m13, old)]
    oen = np.where(o2003, "DJ", sec)
    oen = np.where(empty, None, oen)
    bl = np.where(empty, None, region)

    deliveries, labels = [], []
    plan = {}
    if plant:
        for pid in PLANTED:
            for t in rng.choice(np.arange(3, months), size=int(rng.integers(1, 3)), replace=False):
                plan.setdefault(int(t), []).append((pid, float(rng.uniform(0.15, 0.35)) if pid == "DQ-02" else
                                                   float(rng.uniform(0.002, 0.01)) if pid == "DQ-03" else
                                                   float(rng.uniform(0.6, 1.0)) if pid == "DQ-04" else float(rng.uniform(0.95, 1.0))))
    for t in range(months):
        ws, we = _month_add(START, t - 2).toordinal(), _month_end(_month_add(START, t)).toordinal()
        sel = np.where((begin <= we) & (end >= ws))[0]
        known_end = end[sel] <= we
        late = known_end & (end[sel] > we - 31) & (rng.random(len(sel)) < cal["late_report"] * 3)
        ende = [fmt_date(e) if k and not l else None for e, k, l in zip(end[sel], known_end, late)]
        df = pd.DataFrame({"vvh_id": ids[sel].astype(str), "person_id": person[sel].astype(str), "geburtsdatum": [births[i] for i in sel],
                           "geschlecht": sex[sel], "beginn": [fmt_date(b) for b in begin[sel]], "ende": ende, "qual": qual[sel],
                           "oenace": oen[sel], "bundesland": bl[sel]})
        # phantom double registrations (DQ-16): new VVH of an existing person, gone in the next delivery
        n_ph = int(rng.poisson(len(sel) * bg["phantom"]))
        if n_ph:
            donors = df[df["ende"].isna()].sample(n=min(n_ph, int(df["ende"].isna().sum())), random_state=int(rng.integers(1 << 30)))
            ph = donors.copy()
            ph["vvh_id"] = [str(10_000_000 + t * 10_000 + j) for j in range(len(ph))]
            ph["beginn"] = fmt_date(_month_add(START, t).toordinal() + 3)
            df = pd.concat([df, ph], ignore_index=True)
        for pid, intensity in plan.get(t, []):
            labels.append({"delivery": t, "problem_id": pid, "intensity": round(intensity, 4)})
            if pid == "DQ-01":
                swap = rng.random(len(df)) < intensity
                b, e = df["beginn"].copy(), df["ende"].copy()
                df.loc[swap, "beginn"], df.loc[swap, "ende"] = e[swap], b[swap]
            elif pid == "DQ-02":
                drop_ids = df["vvh_id"].drop_duplicates().sample(frac=intensity, random_state=int(rng.integers(1 << 30)))
                df = df[~df["vvh_id"].isin(set(drop_ids))]
            elif pid == "DQ-03":
                df = pd.concat([df, df.sample(frac=intensity, random_state=int(rng.integers(1 << 30)))], ignore_index=True)
            elif pid == "DQ-04":
                fd = df["qual"].astype(str).str.endswith("FD")
                df = df[~(fd & (rng.random(len(df)) < intensity))]
        deliveries.append(df.reset_index(drop=True))
    return deliveries, labels


def checksum(deliveries: list[pd.DataFrame]) -> str:
    h = hashlib.sha256()
    for df in deliveries:
        h.update(pd.util.hash_pandas_object(df.fillna("∅"), index=False).values.tobytes())
    return h.hexdigest()
