"""Error detector and expected corridor trained on synthetic deliveries (Phase 3b, PRD §5.2), with an honest evaluation.

Populations are kept apart and reported separately:
  synthetic train (seeds 1–8) · synthetic calibration (9–16) · synthetic test (17–20) · the 24 real deliveries
  (labels from Problems.md §2.1: DQ-01 2025-06, DQ-02 2025-10, DQ-03 2025-03, DQ-04 2025-03).
Detector: one RandomForest per planted problem on delivery-level features (same feature code for synthetic and real data).
Corridor: per series the month-over-month log change is predicted by its calendar-month median from the synthetic training
years; the interval comes from conformal quantiles of the calibration residuals (99 %). Outside = suspected data problem.
Outputs: ops.model (hashes, metrics, seed), synth.run / synth.label / synth.prediction, files in models/. Nothing is
written to stat_* or store.*; findings are labelled „Modell“ and only proposed.
"""
import datetime as dt
import hashlib
import io
import json
import pickle

import numpy as np
import pandas as pd

from statagent.config import BASE_DIR, connect, setup_logging
from statagent.ml import synth

MODEL_DIR = BASE_DIR / "models"
FEATURES = ["begin_empty", "end_before_begin", "dup_share", "fd_share", "fd_ratio_prev", "rows_ratio_prev", "active_ratio_prev",
            "retention_prev", "month13_share", "empty_share"]
SERIES = {"total": None, "A": ("sec", "A"), "C": ("sec", "C"), "F": ("sec", "F"), "I": ("sec", "I"), "Tirol": ("bl", "7"), "FD": ("fd", True)}
REAL_LABELS = {"DQ-01": {"2025-06"}, "DQ-02": {"2025-10"}, "DQ-03": {"2025-03"}, "DQ-04": {"2025-03"}}
SPLITS = {"train": range(1, 9), "calibration": range(9, 17), "test": range(17, 21)}
MODEL_SEED = 20261105


def _stichtag(d: dt.date) -> str:
    return synth._month_end(d).isoformat()


def delivery_stats(df: pd.DataFrame, ref: str) -> dict:
    b, e = df["beginn"], df["ende"]
    active = b.notna() & (b <= ref) & (e.isna() | (e >= ref))
    act = df[active]
    sec = act["oenace"].astype(str).str[0]
    out = {"rows": len(df), "active_ids": set(act["vvh_id"]), "ids": set(df["vvh_id"]), "active": act["vvh_id"].nunique(),
           "fd": float(df["qual"].astype(str).str.endswith("FD").mean()) if len(df) else 0.0,
           "begin_empty": float((b.isna() & e.notna()).mean()), "end_before_begin": float((b.notna() & e.notna() & (e < b)).mean()),
           "dup_share": float(df.duplicated().mean()), "month13_share": float((df["geburtsdatum"].astype(str).str[5:7] == "13").mean()),
           "empty_share": float(df["oenace"].isna().mean())}
    out["series"] = {"total": out["active"]}
    for name, spec in SERIES.items():
        if spec is None:
            continue
        kind, val = spec
        if kind == "sec":
            out["series"][name] = int(act.loc[sec == val, "vvh_id"].nunique())
        elif kind == "bl":
            out["series"][name] = int(act.loc[act["bundesland"].astype(str) == val, "vvh_id"].nunique())
        else:
            out["series"][name] = int(act.loc[act["qual"].astype(str).str.endswith("FD"), "vvh_id"].nunique())
    return out


def features(cur: dict, prev: dict | None) -> dict:
    f = {k: cur[k] for k in ("begin_empty", "end_before_begin", "dup_share", "month13_share", "empty_share")}
    f["fd_share"] = cur["fd"]
    if prev:
        f["fd_ratio_prev"] = cur["fd"] / prev["fd"] if prev["fd"] else 1.0
        f["rows_ratio_prev"] = cur["rows"] / prev["rows"] if prev["rows"] else 1.0
        f["active_ratio_prev"] = cur["active"] / prev["active"] if prev["active"] else 1.0
        f["retention_prev"] = len(prev["active_ids"] & cur["ids"]) / len(prev["active_ids"]) if prev["active_ids"] else 1.0
    else:
        f.update(fd_ratio_prev=1.0, rows_ratio_prev=1.0, active_ratio_prev=1.0, retention_prev=1.0)
    return f


def synthetic_population(cal: dict, seeds, scale: float, log) -> tuple[pd.DataFrame, list[dict], list[str]]:
    rows, checks = [], []
    for seed in seeds:
        deliveries, labels = synth.simulate(cal, seed, scale=scale)
        checks.append(synth.checksum(deliveries))
        lab = {(l["delivery"], l["problem_id"]) for l in labels}
        prev = None
        for t, df in enumerate(deliveries):
            ref = _stichtag(synth._month_add(synth.START, t))
            st = delivery_stats(df, ref)
            f = features(st, prev)
            rows.append({"seed": seed, "t": t, "cal": synth._month_add(synth.START, t).month, **f,
                         **{f"y_{pid}": int((t, pid) in lab) for pid in synth.PLANTED},
                         **{f"s_{k}": v for k, v in st["series"].items()}})
            prev = st
        log.info("  synthetic run seed %s: %s deliveries, %s planted errors, checksum %s", seed, len(deliveries), len(labels), checks[-1][:12])
    return pd.DataFrame(rows), [], checks


def real_population(conn) -> pd.DataFrame:
    months = [r[0] for r in conn.execute("SELECT lieferung FROM roh.ladeprotokoll ORDER BY 1").fetchall()]
    rows, prev = [], None
    for m in months:
        buf = io.StringIO()
        with conn.cursor().copy(f"COPY (SELECT {', '.join(synth.COLUMNS)} FROM roh.lieferung WHERE lieferung = '{m}') TO STDOUT WITH CSV HEADER") as cp:
            for chunk in cp:
                buf.write(bytes(chunk).decode("utf-8"))
        buf.seek(0)
        df = pd.read_csv(buf, dtype=str, keep_default_na=False, na_values=[""])
        ref = _stichtag(dt.date(int(m[:4]), int(m[5:]), 1))
        st = delivery_stats(df, ref)
        rows.append({"delivery": m, "cal": int(m[5:]), **features(st, prev),
                     **{f"y_{pid}": int(m in REAL_LABELS[pid]) for pid in synth.PLANTED}, **{f"s_{k}": v for k, v in st["series"].items()}})
        prev = st
    return pd.DataFrame(rows)


def _prf(y, p) -> dict:
    tp, fp, fn = int(((p == 1) & (y == 1)).sum()), int(((p == 1) & (y == 0)).sum()), int(((p == 0) & (y == 1)).sum())
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    f1 = 2 * prec * rec / (prec + rec) if prec and rec else (0.0 if (prec is not None or rec is not None) else None)
    return {"tp": tp, "fp": fp, "fn": fn, "precision": prec, "recall": rec, "f1": f1, "positives": int(y.sum()), "n": int(len(y))}


def train_detector(train: pd.DataFrame):
    """One standardized logistic regression per planted problem (few positives → a simple, explainable model)."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    models = {}
    for pid in synth.PLANTED:
        clf = make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", C=1.0, max_iter=5000, random_state=MODEL_SEED))
        clf.fit(train[FEATURES].values, train[f"y_{pid}"].values)
        models[pid] = clf
    return models


def drivers(clf, x: np.ndarray, n: int = 3) -> list[str]:
    """Features that pushed the probability up most: coefficient × standardized value."""
    scaler, lr = clf.steps[0][1], clf.steps[-1][1]
    contrib = lr.coef_[0] * (x - scaler.mean_) / scaler.scale_
    return [FEATURES[j] for j in np.argsort(contrib)[::-1][:n]]


def corridor_fit(train: pd.DataFrame, calib: pd.DataFrame, alpha: float = 0.01) -> dict:
    def logret(df):
        out = []
        for seed, g in df.sort_values(["seed", "t"]).groupby("seed"):
            for name in SERIES:
                v = g[f"s_{name}"].values.astype(float)
                clean = (g[[f"y_{p}" for p in synth.PLANTED]].sum(axis=1).values == 0)
                for i in range(1, len(v)):
                    if v[i - 1] > 0 and v[i] > 0 and clean[i] and clean[i - 1]:
                        out.append({"series": name, "cal": int(g["cal"].values[i]), "r": float(np.log(v[i] / v[i - 1]))})
        return pd.DataFrame(out)
    tr, ca = logret(train), logret(calib)
    med = tr.groupby(["series", "cal"])["r"].median().to_dict()
    ca["res"] = ca["r"] - [med.get((s, c), 0.0) for s, c in zip(ca["series"], ca["cal"])]
    def conformal(x, level):          # finite-sample conformal quantile: ceil((n + 1) · level) / n
        n = len(x)
        return float(np.quantile(x, min(1.0, np.ceil((n + 1) * level) / n), method="higher"))
    q = {s: (-conformal(-g["res"].values, 1 - alpha / 2), conformal(g["res"].values, 1 - alpha / 2)) for s, g in ca.groupby("series")}
    return {"median": {f"{s}|{c}": v for (s, c), v in med.items()}, "quantiles": q, "alpha": alpha}


def corridor_apply(series: dict[str, list[float]], cals: list[int], model: dict) -> dict[str, list[dict]]:
    """Expected value, band and flag per month; a flagged month is not used as the base of the next prediction."""
    out = {}
    for name, values in series.items():
        lo_q, hi_q = model["quantiles"].get(name, (-0.05, 0.05))
        base, alt_base, res = None, None, []
        for i, v in enumerate(values):
            if i == 0 or base is None or base <= 0:
                res.append({"expected": None, "lower": None, "upper": None, "actual": v, "flag": False})
                base = v
                continue
            r = model["median"].get(f"{name}|{cals[i]}", 0.0)
            exp, lower, upper = base * np.exp(r), base * np.exp(r + lo_q), base * np.exp(r + hi_q)
            flag = not (lower <= v <= upper)
            if flag and alt_base is not None:
                # previous month was flagged: a value that fits the band from the previous *actual* value is a level
                # shift that persists (e.g. the ÖNACE switch), not a new error → accept it
                a_lower, a_upper = alt_base * np.exp(r + lo_q), alt_base * np.exp(r + hi_q)
                if a_lower <= v <= a_upper:
                    exp, lower, upper, flag = alt_base * np.exp(r), a_lower, a_upper, False
            res.append({"expected": float(exp), "lower": float(lower), "upper": float(upper), "actual": v, "flag": bool(flag)})
            alt_base = v if flag else None
            base = exp if flag else v
        out[name] = res
    return out


def _hash_obj(obj) -> str:
    return hashlib.sha256(pickle.dumps(obj, protocol=4)).hexdigest()


def train_all(scale: float = 0.05) -> dict:
    log = setup_logging("modelle")
    MODEL_DIR.mkdir(exist_ok=True)
    with connect() as conn:
        cal = synth.calibrate(conn)
        log.info("calibration hash %s", cal["hash"][:16])
        pops = {name: synthetic_population(cal, seeds, scale, log) for name, seeds in SPLITS.items()}
        real = real_population(conn)
    train, calib, test = pops["train"][0], pops["calibration"][0], pops["test"][0]
    detector = train_detector(train)
    corridor = corridor_fit(train, calib)
    metrics = {"detector": {}, "corridor": {}}
    for pop_name, df in (("synthetic_test", test), ("real_24", real)):
        metrics["detector"][pop_name] = {}
        for pid, clf in detector.items():
            pred = clf.predict(df[FEATURES].values)
            metrics["detector"][pop_name][pid] = _prf(df[f"y_{pid}"].values, pred)
    # corridor: coverage on clean synthetic test months, detection of planted DQ-02/DQ-04, flags in the real deliveries
    cov_in, cov_n, det = 0, 0, {"DQ-02": [0, 0], "DQ-04": [0, 0]}
    for seed, g in test.sort_values(["seed", "t"]).groupby("seed"):
        res = corridor_apply({s: list(g[f"s_{s}"].astype(float)) for s in SERIES}, list(g["cal"]), corridor)
        planted = g[[f"y_{p}" for p in synth.PLANTED]].values
        for i in range(1, len(g)):
            clean = planted[i].sum() == 0 and planted[i - 1].sum() == 0
            if clean:
                for s in SERIES:
                    cov_n += 1
                    cov_in += 0 if res[s][i]["flag"] else 1
            if g["y_DQ-02"].values[i]:
                det["DQ-02"][1] += 1
                det["DQ-02"][0] += int(res["total"][i]["flag"])
            if g["y_DQ-04"].values[i]:
                det["DQ-04"][1] += 1
                det["DQ-04"][0] += int(res["FD"][i]["flag"])
    real_res = corridor_apply({s: list(real[f"s_{s}"].astype(float)) for s in SERIES}, list(real["cal"]), corridor)
    real_flags = [{"series": s, "delivery": real["delivery"].values[i], **r} for s, rs in real_res.items() for i, r in enumerate(rs) if r["flag"]]
    metrics["corridor"] = {"synthetic_test_coverage": round(cov_in / cov_n, 4) if cov_n else None, "synthetic_test_points": cov_n,
                           "synthetic_detection": {k: {"found": v[0], "planted": v[1]} for k, v in det.items()},
                           "real_flags": [{k: (round(v) if isinstance(v, float) else v) for k, v in f.items()} for f in real_flags],
                           "nominal_coverage": 1 - corridor["alpha"]}
    det_bytes = pickle.dumps(detector, protocol=4)
    (MODEL_DIR / "detector.pkl").write_bytes(det_bytes)
    (MODEL_DIR / "corridor.json").write_text(json.dumps(corridor, indent=1), encoding="utf-8")
    data_hash = hashlib.sha256(pd.util.hash_pandas_object(train[FEATURES + [f"y_{p}" for p in synth.PLANTED]], index=False).values.tobytes()).hexdigest()
    with connect() as conn, conn.transaction():
        synth_run = conn.execute("""INSERT INTO ops.run (kind, note, status, finished_at, checksum) VALUES ('synth', %s, 'done', now(), %s)
                                    RETURNING run_id""", (f"{sum(len(s) for s in SPLITS.values())} synthetische Läufe à 36 Lieferungen, Maßstab {scale}",
                                                          hashlib.sha256("".join(c for p in pops.values() for c in p[2]).encode()).hexdigest())).fetchone()[0]
        for name, (df, _, checks) in pops.items():
            for seed, chk in zip(SPLITS[name], checks):
                conn.execute("INSERT INTO synth.run (synth_run, seed, split, scale, months, checksum, calibration_hash) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                             (synth_run, seed, name, scale, 36, chk, cal["hash"]))
            for r in df.to_dict("records"):
                for pid in synth.PLANTED:
                    if r[f"y_{pid}"]:
                        conn.execute("INSERT INTO synth.label (synth_run, seed, delivery_index, problem_id) VALUES (%s, %s, %s, %s)",
                                     (synth_run, int(r["seed"]), int(r["t"]), pid))
        ids = {}
        for kind, obj, m in (("detector", detector, metrics["detector"]), ("corridor", corridor, metrics["corridor"])):
            ids[kind] = conn.execute("""INSERT INTO ops.model (kind, version, data_hash, model_hash, metrics, seed, note, synth_run)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING model_id""",
                                     (kind, "1.0", data_hash, hashlib.sha256(det_bytes).hexdigest() if kind == "detector" else _hash_obj(corridor),
                                      json.dumps(m, default=float), MODEL_SEED, f"Maßstab {scale}, Kalibrierung {cal['hash'][:16]}", synth_run)).fetchone()[0]
        for i, r in real.iterrows():
            probs = {pid: float(clf.predict_proba(r[FEATURES].values.reshape(1, -1).astype(float))[0][1]) for pid, clf in detector.items()}
            for pid, p in probs.items():
                top = drivers(detector[pid], r[FEATURES].values.astype(float))
                conn.execute("""INSERT INTO synth.prediction (model_id, delivery, series, expected, lower, upper, actual, flag, probability, features)
                                VALUES (%s, %s, %s, NULL, NULL, NULL, NULL, %s, %s, %s)""",
                             (ids["detector"], r["delivery"], pid, p >= 0.5, round(p, 4), json.dumps({f: round(float(r[f]), 5) for f in top})))
        for s, rs in real_res.items():
            for i, r in enumerate(rs):
                conn.execute("""INSERT INTO synth.prediction (model_id, delivery, series, expected, lower, upper, actual, flag)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                             (ids["corridor"], real["delivery"].values[i], s, r["expected"], r["lower"], r["upper"], r["actual"], r["flag"]))
    log.info("models trained: %s", json.dumps(metrics, default=float)[:2000])
    return {"metrics": metrics, "models": ids, "synth_run": synth_run, "calibration_hash": cal["hash"]}
