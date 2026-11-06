"""JSON API for the web UI. Read endpoints query the database; actions (runs, approvals, exports, agent) go through the
same deterministic functions as the CLI. Long actions stream progress as Server-Sent Events (text/event-stream):
  event: progress  data: {"step", "pct", "detail"}
  event: result    data: {...}
  event: error     data: {"message"}
Approvals need a named person (T7); the API never approves anything on its own.
Bound to 127.0.0.1 only (local and offline, T2).
"""
import datetime as dt
import decimal
import json
import os
import queue
import threading
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from statagent.config import BASE_DIR, connect
from statagent.core.labels import RULE_STATUS, RUN_KIND, RUN_STATUS, label

app = FastAPI(title="StatAgent API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
                   allow_methods=["*"], allow_headers=["*"])
_job_lock = threading.Lock()


def _jsonable(v):
    if isinstance(v, (dt.date, dt.datetime)):
        return v.isoformat()
    if isinstance(v, decimal.Decimal):
        return int(v) if v == v.to_integral_value() else float(v)
    return v


def rows(sql: str, params=None) -> list[dict]:
    with connect() as conn:
        cur = conn.execute(sql, params)
        cols = [c.name for c in cur.description]
        return [{k: _jsonable(v) for k, v in zip(cols, r)} for r in cur.fetchall()]


def one(sql: str, params=None) -> dict | None:
    r = rows(sql, params)
    return r[0] if r else None


def _dump(obj) -> str:
    return json.dumps(obj, default=_jsonable, ensure_ascii=False)


def stream_job(fn, *args, **kwargs) -> StreamingResponse:
    """Run `fn(progress, *args)` in a thread and stream its progress and result as SSE."""
    q: queue.Queue = queue.Queue()

    def progress(step, pct, detail):
        q.put(("progress", {"step": step, "pct": pct, "detail": detail}))

    def worker():
        if not _job_lock.acquire(blocking=False):
            q.put(("error", {"message": "Es läuft bereits ein anderer Auftrag – bitte warten."}))
            q.put(None)
            return
        try:
            q.put(("result", fn(progress, *args, **kwargs)))
        except Exception as exc:  # shown to the user, never hidden
            q.put(("error", {"message": str(exc)}))
        finally:
            _job_lock.release()
            q.put(None)

    threading.Thread(target=worker, daemon=True).start()

    def events():
        while True:
            try:
                item = q.get(timeout=15)
            except queue.Empty:
                yield ": keep-alive\n\n"
                continue
            if item is None:
                break
            kind, data = item
            yield f"event: {kind}\ndata: {_dump(data)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# --- system --------------------------------------------------------------------------------------

@app.get("/api/health")
def health():
    from statagent.agents.llm import llm_status
    db = one("SELECT current_database() AS db, version() AS version, now() AS now")
    return {"ok": True, "db": db, "llm": llm_status(), "offline_ready": True,
            "fragen_person": os.environ.get("STATAGENT_FRAGEN_PERSON", "").strip() or "Gast"}


@app.get("/api/users")
def users():
    names = [n.strip() for n in os.environ.get("STATAGENT_USERS", "").split(",") if n.strip()]
    return {"users": names, "free_entry": True,
            "hint": "Freigaben brauchen den Namen einer Person (T7); Platzhalter wie „Team“ werden abgelehnt."}


@app.get("/api/overview")
def overview():
    """Start page: key facts with evidence links."""
    with connect() as conn:
        stats = {k: v for k, v in conn.execute("""
            SELECT 'deliveries', count(*)::bigint FROM roh.ladeprotokoll UNION ALL
            SELECT 'rows', coalesce(sum(zeilen), 0)::bigint FROM roh.ladeprotokoll UNION ALL
            SELECT 'files', count(*)::bigint FROM roh.file UNION ALL
            SELECT 'runs_done', count(*)::bigint FROM ops.run WHERE kind = 'month' AND status = 'done' UNION ALL
            SELECT 'rules_approved', count(*)::bigint FROM ops.rule WHERE status = 'approved' UNION ALL
            SELECT 'rules_proposed', count(*)::bigint FROM ops.rule WHERE status = 'proposed' UNION ALL
            SELECT 'findings', count(*)::bigint FROM ops.finding f WHERE run_id IN (SELECT max(run_id) FROM ops.run WHERE kind='month' AND status='done' GROUP BY delivery, rule_set) UNION ALL
            SELECT 'klass_entries', (SELECT count(*) FROM klass_alle)::bigint UNION ALL
            SELECT 'transitions', (SELECT count(*) FROM klass_uebergang)::bigint""").fetchall()}
    series = rows("""SELECT regelwerk, substr(stand, 11) AS monat, sum(wert)::bigint AS wert, min(status) AS status
                     FROM stat_beschaeftigte GROUP BY 1, 2 ORDER BY 1, 2""")
    return {"stats": stats, "series": series}


# --- Lieferungen ---------------------------------------------------------------------------------

@app.get("/api/lieferungen")
def deliveries():
    data = rows("""SELECT p.lieferung AS month, p.datei AS file_name, p.zeilen AS rows, f.path, f.sha256, f.size_bytes, f.loaded_at
                   FROM roh.ladeprotokoll p LEFT JOIN roh.file f ON f.path = 'lieferungen/' || p.datei
                   ORDER BY p.lieferung""")
    profile = {}
    for r in rows("SELECT delivery, metric, value FROM store.profile"):
        profile.setdefault(r["delivery"], {})[r["metric"]] = r["value"]
    runs = {}
    for r in rows("""SELECT DISTINCT ON (delivery, rule_set) delivery, rule_set, run_id, checksum, finished_at, status
                     FROM ops.run WHERE kind = 'month' AND status = 'done' ORDER BY delivery, rule_set, run_id DESC"""):
        runs.setdefault(r["delivery"], {})[r["rule_set"]] = r
    for d in data:
        d["profile"] = profile.get(d["month"], {})
        d["runs"] = runs.get(d["month"], {})
    return {"deliveries": data}


@app.get("/api/dateien")
def files(area: str | None = None):
    return {"files": rows("""SELECT path, area, format, size_bytes, sha256, encoding, units, loaded_at FROM roh.file
                             WHERE %(a)s::text IS NULL OR area = %(a)s ORDER BY area, path""", {"a": area})}


def _verify_job(progress):
    from statagent.etl.load import iter_files, sha256
    progress("start", 2, "Prüfsummen aller Paketdateien werden berechnet …")
    with connect() as conn:
        registered = dict(conn.execute("SELECT path, sha256 FROM roh.file").fetchall())
        on_disk = {p.relative_to(BASE_DIR).as_posix(): p for _, p in iter_files()}
        results = []
        names = sorted(set(registered) | set(on_disk))
        for i, rel in enumerate(names, start=1):
            if rel not in on_disk:
                state = "fehlt auf der Festplatte"
            elif rel not in registered:
                state = "noch nicht geladen"
            else:
                state = "unverändert" if sha256(on_disk[rel]) == registered[rel] else "VERÄNDERT"
            results.append({"path": rel, "state": state, "sha256": registered.get(rel)})
            if i % 10 == 0 or i == len(names):
                progress("files", 2 + int(80 * i / len(names)), f"{i}/{len(names)} Dateien geprüft")
        progress("rows", 85, "Zeilenzahlen der Lieferungen werden gezählt …")
        counts = conn.execute("""SELECT p.lieferung, p.zeilen, count(l.*) FROM roh.ladeprotokoll p
                                 LEFT JOIN roh.lieferung l USING (lieferung) GROUP BY 1, 2 ORDER BY 1""").fetchall()
    total = sum(c[2] for c in counts)
    ok = all(r["state"] == "unverändert" for r in results) and all(c[1] == c[2] for c in counts) and total == 10_152_292
    progress("done", 100, f"{len(results)} Dateien, {total:,} Zeilen – {'OK' if ok else 'PROBLEME'}".replace(",", "."))
    return {"ok": ok, "files": results, "deliveries": [{"month": c[0], "logged": c[1], "actual": c[2]} for c in counts],
            "total_rows": total, "expected_rows": 10_152_292, "checked_at": dt.datetime.now().isoformat()}


@app.post("/api/pruefen")
def verify():
    return stream_job(_verify_job)


@app.get("/api/profil")
def store_profile():
    from statagent.etl.store import COLUMNS
    data = {}
    for r in rows("SELECT delivery, metric, value FROM store.profile ORDER BY delivery"):
        data.setdefault(r["delivery"], {"month": r["delivery"]})[r["metric"]] = r["value"]
    return {"columns": [{"key": k, "label": h} for k, h in COLUMNS], "rows": list(data.values())}


# --- Läufe ---------------------------------------------------------------------------------------

@app.get("/api/laeufe")
def runs(kind: str | None = None, limit: int = Query(200, le=1000)):
    data = rows("""SELECT run_id, kind, delivery, rule_set, rules, started_at, finished_at, status, row_count, checksum, note
                   FROM ops.run WHERE %(k)s::text IS NULL OR kind = %(k)s ORDER BY run_id DESC LIMIT %(l)s""",
                {"k": kind, "l": limit})
    for r in data:
        r["kind_label"], r["status_label"] = label(RUN_KIND, r["kind"]), label(RUN_STATUS, r["status"])
    return {"runs": data}


@app.get("/api/laeufe/{run_id}")
def run_detail(run_id: int):
    run = one("SELECT * FROM ops.run WHERE run_id = %s", (run_id,))
    if not run:
        raise HTTPException(404, f"Lauf {run_id} nicht gefunden")
    metrics = {r["metric"]: r["value"] for r in rows("SELECT metric, value FROM ops.run_metric WHERE run_id = %s", (run_id,))}
    findings = rows("SELECT * FROM ops.finding WHERE run_id = %s ORDER BY finding_id", (run_id,))
    revisions = rows("SELECT * FROM ops.revision WHERE run_id = %s ORDER BY month", (run_id,))
    report = one("""SELECT report_id, path, sha256, created_at FROM ops.report WHERE run_id = %s AND kind = 'quality_report'
                    ORDER BY report_id DESC LIMIT 1""", (run_id,))
    return {"run": run, "metrics": metrics, "findings": findings, "revisions": revisions, "report": report}


class RunRequest(BaseModel):
    lieferung: str
    regelwerk: str = "basis"
    vorschau: list[str] = []


def _run_job(progress, month, rule_set, preview):
    from statagent.qa.run import run
    return run(month, rule_set, tuple(preview), progress=progress)


@app.post("/api/laeufe")
def start_run(req: RunRequest):
    return stream_job(_run_job, req.lieferung, req.regelwerk, req.vorschau)


def _run_all_job(progress, rule_set):
    from statagent.qa.run import all_months, run
    with connect() as conn:
        months = all_months(conn)
    out = []
    for i, m in enumerate(months):
        def sub(step, pct, detail, i=i, m=m):
            progress(step, int(100 * (i + pct / 100) / len(months)), f"[{i + 1}/{len(months)}] {m}: {detail}")
        r = run(m, rule_set, progress=sub)
        out.append({k: r[k] for k in ("run_id", "month", "checksum", "findings")} | {"total": r["metrics"]["records_total"]})
    return {"runs": out, "rule_set": rule_set}


@app.post("/api/gesamtlauf")
def start_run_all(regelwerk: str = "basis"):
    return stream_job(_run_all_job, regelwerk)


# --- Qualitätsberichte, Auffälligkeiten, Rückfragen ---------------------------------------------

@app.get("/api/qualitaetsberichte")
def quality_reports(regelwerk: str = "basis"):
    # latest report per month FIRST, then the per-report figures (before: computed for every older report too → ~18 s)
    return {"reports": rows("""
        WITH latest AS (
          SELECT DISTINCT ON (r.month) r.month, r.rule_set, r.run_id, r.path, r.sha256, r.created_at, u.checksum
          FROM ops.report r JOIN ops.run u ON u.run_id = r.run_id AND u.status = 'done'
          WHERE r.kind = 'quality_report' AND r.rule_set = %(rs)s AND u.note IS NULL
          ORDER BY r.month, r.report_id DESC),
        published AS (SELECT substr(stand, 11) AS month, max(status) AS status FROM stat_beschaeftigte
                      WHERE regelwerk = %(rs)s GROUP BY 1)
        SELECT l.*,
               (SELECT count(*) FROM ops.finding f WHERE f.run_id = l.run_id) AS findings,
               (SELECT count(*) FROM ops.finding f WHERE f.run_id = l.run_id AND f.classification = 'unexplained') AS unexplained,
               (SELECT value FROM ops.run_metric m WHERE m.run_id = l.run_id AND m.metric = 'records_total') AS total,
               p.status
        FROM latest l LEFT JOIN published p USING (month) ORDER BY l.month""", {"rs": regelwerk})}


@app.get("/api/qualitaetsberichte/{regelwerk}/{monat}")
def quality_report(regelwerk: str, monat: str):
    rep = one("""SELECT r.* FROM ops.report r JOIN ops.run u ON u.run_id = r.run_id AND u.status = 'done' AND u.note IS NULL
                 WHERE r.kind = 'quality_report' AND r.rule_set = %s AND r.month = %s ORDER BY r.report_id DESC LIMIT 1""",
              (regelwerk, monat))
    if not rep:
        raise HTTPException(404, f"Kein Qualitätsbericht für {monat} ({regelwerk}) – zuerst den Lauf starten")
    detail = run_detail(rep["run_id"])
    return {"report": rep, **{k: detail[k] for k in ("run", "metrics", "findings", "revisions")}}


@app.get("/api/rueckfragen")
def inquiries():
    return {"inquiries": rows("SELECT * FROM ops.inquiry ORDER BY inquiry_id")}


@app.get("/api/annahmen")
def assumptions():
    """All rules with their assumption and justification, plus how many records each affected per month."""
    rules_ = rows("SELECT * FROM ops.rule ORDER BY rule_id")
    hits = rows("""SELECT r AS rule_id, rule_set, month, count(*)::bigint AS n FROM store.month_record, unnest(rules) r
                   GROUP BY 1, 2, 3 ORDER BY 1, 2, 3""")
    for r in rules_:
        r["status_label"] = label(RULE_STATUS, r["status"])
        r["hits"] = [h for h in hits if h["rule_id"] == r["rule_id"]]
    return {"rules": rules_}


# --- Statistik (deterministic tools) -------------------------------------------------------------

class StatQuery(BaseModel):
    regelwerk: str = "basis"
    monate: list[str] = []
    dimensionen: list[str] = []
    filter: dict[str, Any] = {}
    kennzahl: str = "bestand"


@app.post("/api/statistik")
def statistic(q: StatQuery):
    from statagent.reporting.tools import ToolError, query_stat
    with connect() as conn:
        try:
            return query_stat(conn, q.regelwerk, q.monate or None, q.dimensionen, q.filter, q.kennzahl)
        except ToolError as exc:
            raise HTTPException(422, str(exc))


@app.get("/api/statistik/monate")
def stat_months(regelwerk: str = "basis"):
    return {"months": [r["m"] for r in rows("SELECT DISTINCT substr(stand, 11) AS m FROM stat_beschaeftigte WHERE regelwerk = %s ORDER BY 1",
                                            (regelwerk,))]}


class EvidenceQuery(BaseModel):
    regelwerk: str = "basis"
    monat: str
    filter: dict[str, Any] = {}
    limit: int = 5
    vvh_ids: list[str] = []


@app.post("/api/quellennachweis")
def source_evidence(q: EvidenceQuery):
    from statagent.reporting.tools import ToolError, evidence, example_records
    with connect() as conn:
        try:
            ex = example_records(conn, q.regelwerk, q.monat, q.filter, q.limit, q.vvh_ids or None)
        except ToolError as exc:
            raise HTTPException(422, str(exc))
        ev = evidence(conn, q.regelwerk, [q.monat])
    return {"evidence": ev, "examples": ex}


# --- Regeln und Freigaben ------------------------------------------------------------------------

@app.get("/api/regeln")
def rules_list():
    data = rows("SELECT * FROM ops.rule ORDER BY rule_id")
    for r in data:
        r["status_label"] = label(RULE_STATUS, r["status"])
    return {"rules": data}


@app.get("/api/regeln/{rule_id}")
def rule(rule_id: str):
    r = one("SELECT * FROM ops.rule WHERE rule_id = %s", (rule_id,))
    if not r:
        raise HTTPException(404, f"Regel {rule_id} existiert nicht")
    r["status_label"] = label(RULE_STATUS, r["status"])
    r["approvals"] = rows("SELECT * FROM ops.approval WHERE object_type = 'rule' AND object_id = %s ORDER BY decided_at", (rule_id,))
    return r


class Decision(BaseModel):
    person: str
    approve: bool
    comment: str | None = None


@app.post("/api/regeln/{rule_id}/entscheidung")
def decide_rule(rule_id: str, d: Decision):
    from statagent.core import rules as rules_mod
    try:
        with connect() as conn:
            decision = rules_mod.decide(conn, rule_id, d.person, d.approve, d.comment)
            action = (rules_mod.rule_details(conn, rule_id) or {}).get("action")
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    from statagent.core import change_log
    with connect() as conn:
        change_log.export(conn)
    next_step = ("Klassifikationen neu aufbauen" if action == "source_mapping" else "betroffene Monate neu rechnen (Läufe)")
    return {"rule_id": rule_id, "decision": decision, "person": d.person.strip(), "next": next_step}


@app.get("/api/freigaben")
def approvals():
    return {"approvals": rows("SELECT * FROM ops.approval ORDER BY decided_at DESC"),
            "pending_rules": rows("SELECT * FROM ops.rule WHERE status = 'proposed' ORDER BY rule_id"),
            "pending_code": rows("SELECT * FROM ops.code_proposal WHERE status = 'proposed' ORDER BY proposal_id")
            if one("SELECT to_regclass('ops.code_proposal') IS NOT NULL AS x")["x"] else []}


class PublishRequest(BaseModel):
    person: str
    regelwerk: str = "basis"
    lieferung: str | None = None
    comment: str | None = None


@app.post("/api/veroeffentlichen")
def publish(req: PublishRequest):
    from statagent.qa.run import publish as do_publish
    try:
        months = do_publish(req.person, req.regelwerk, req.lieferung, req.comment)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return {"published": months, "person": req.person.strip()}


@app.get("/api/protokoll")
def protocol():
    from statagent.core import change_log
    with connect() as conn:
        entries = change_log.entries(conn)
        msg = change_log.commit_message(conn)
    keys = ("log_id", "logged_at", "object", "change", "instruction", "approved_by", "git_commit")
    return {"entries": [{k: _jsonable(v) for k, v in zip(keys, e)} for e in reversed(entries)], "commit_message": msg}


# --- Klassifikationen ----------------------------------------------------------------------------

KLASS = {"region": "klass_region", "oenace": "klass_oenace", "geschlecht": "klass_geschlecht",
         "qualifikation": "klass_qualifikation", "alter": "klass_alter"}


@app.get("/api/klassifikationen")
def classifications():
    summary = rows("""SELECT klassifikation, version, ebene, count(*)::bigint AS n, min(gueltig_von) AS von, max(gueltig_bis) AS bis
                      FROM klass_alle GROUP BY 1, 2, 3 ORDER BY 1, 2, 3""")
    transitions = rows("""SELECT klassifikation, version_alt, version_neu, beziehung, count(*)::bigint AS n
                          FROM klass_uebergang GROUP BY 1, 2, 3, 4 ORDER BY 1, 2, 3, 4""")
    mappings = rows("""SELECT q.*, r.status AS rule_status FROM quellzuordnung q LEFT JOIN ops.rule r ON r.rule_id = q.regel_id
                       WHERE q.regel_id IS NOT NULL ORDER BY q.merkmal, q.quellwert, q.gueltig_von""")
    run = one("SELECT run_id, checksum, finished_at FROM ops.run WHERE kind = 'classification' AND status = 'done' ORDER BY run_id DESC LIMIT 1")
    return {"summary": summary, "transitions": transitions, "mappings": mappings, "run": run}


@app.get("/api/klassifikationen/{klass}")
def classification_entries(klass: str, version: str | None = None, ebene: str | None = None, q: str | None = None,
                           parent: str | None = None, limit: int = Query(300, le=3000)):
    if klass not in KLASS:
        raise HTTPException(404, f"Klassifikation {klass} unbekannt")
    return {"entries": rows(f"""SELECT version, code, bezeichnung, ebene, uebergeordnet, gueltig_von, gueltig_bis, attribute
                               FROM {KLASS[klass]}
                               WHERE (%(v)s::text IS NULL OR version = %(v)s) AND (%(e)s::text IS NULL OR ebene = %(e)s)
                                 AND (%(p)s::text IS NULL OR uebergeordnet = %(p)s)
                                 AND (%(q)s::text IS NULL OR code ILIKE %(q)s || '%%' OR bezeichnung ILIKE '%%' || %(q)s || '%%')
                               ORDER BY version, length(code), code LIMIT %(l)s""",
                            {"v": version, "e": ebene, "p": parent, "q": q, "l": limit})}


@app.get("/api/klassifikationen/{klass}/{code}/erklaerung")
def explain_code(klass: str, code: str, version: str | None = None):
    from statagent.reporting.explain import explain
    if klass not in KLASS:
        raise HTTPException(404, f"Klassifikation {klass} unbekannt")
    with connect() as conn:
        text = explain(conn, klass, code, version)
    sql_t = """SELECT * FROM klass_uebergang WHERE klassifikation = %(k)s AND (code_alt = %(c)s OR code_neu = %(c)s)
               AND (%(v)s::text IS NULL OR version_alt = %(v)s OR version_neu = %(v)s) ORDER BY gueltig_ab, version_alt, code_alt"""
    edges = rows(sql_t, {"k": KLASS[klass], "c": code, "v": version})
    # second hop: the other codes' transitions (to show splits/merges as a graph)
    others = {(e["version_neu"], e["code_neu"]) for e in edges} | {(e["version_alt"], e["code_alt"]) for e in edges}
    more = []
    for v, c in list(others)[:40]:
        if c != code:
            more += rows("""SELECT * FROM klass_uebergang WHERE klassifikation = %s AND ((version_alt = %s AND code_alt = %s)
                            OR (version_neu = %s AND code_neu = %s))""", (KLASS[klass], v, c, v, c))
    seen, graph = set(), []
    for e in edges + more:
        key = (e["version_alt"], e["code_alt"], e["version_neu"], e["code_neu"])
        if key not in seen:
            seen.add(key)
            graph.append(e)
    names = {}
    for e in graph:
        for v, c in ((e["version_alt"], e["code_alt"]), (e["version_neu"], e["code_neu"])):
            if (v, c) not in names:
                r = one(f"SELECT bezeichnung FROM {KLASS[klass]} WHERE version = %s AND code = %s", (v, c))
                names[(v, c)] = r["bezeichnung"] if r else None
    nodes = [{"id": f"{v}|{c}", "version": v, "code": c, "label": n} for (v, c), n in names.items()]
    return {"text": text, "edges": graph[:200], "nodes": nodes[:200]}


# --- exports, agent, chat (registered by their modules) -----------------------------------------

def _include_optional_routers():
    for module in ("statagent.api.exports", "statagent.api.agent"):
        try:
            mod = __import__(module, fromlist=["router"])
            app.include_router(mod.router)
        except ModuleNotFoundError as exc:
            if exc.name != module:
                raise


_include_optional_routers()


@app.exception_handler(Exception)
def unhandled(_, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": f"Interner Fehler: {exc}"})
