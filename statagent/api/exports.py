"""API routes for the deliverables: Aggregations-Sheets, Open-Data-File, ministry delivery, generated files."""
import hashlib
import json
import queue
import threading

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from statagent.config import BASE_DIR, connect

router = APIRouter()
ABGABE = BASE_DIR / "abgabe"
KINDS = {".xlsx": "Aggregations-Sheet", ".csv": "CSV", ".gz": "Open-Data-File", ".md": "Bericht"}


def _job(fn) -> StreamingResponse:
    q: queue.Queue = queue.Queue()

    def worker():
        try:
            q.put(("progress", {"pct": 5, "detail": "wird erzeugt …"}))
            q.put(("result", fn()))
        except Exception as exc:
            q.put(("error", {"message": str(exc)}))
        finally:
            q.put(None)

    threading.Thread(target=worker, daemon=True).start()

    def events():
        while True:
            item = q.get()
            if item is None:
                break
            yield f"event: {item[0]}\ndata: {json.dumps(item[1], ensure_ascii=False, default=str)}\n\n"
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.get("/api/exporte")
def deliverables():
    files = []
    for p in sorted(ABGABE.rglob("*")) if ABGABE.exists() else []:
        if p.is_file():
            files.append({"path": p.relative_to(BASE_DIR).as_posix(), "kind": KINDS.get(p.suffix, p.suffix), "size": p.stat().st_size,
                          "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "modified": p.stat().st_mtime})
    with connect() as conn:
        approvals = [dict(zip(("object_id", "person", "decided_at"), r)) for r in conn.execute(
            "SELECT object_id, person, decided_at FROM ops.approval WHERE object_type = 'delivery' ORDER BY decided_at DESC").fetchall()]
    for f in files:
        f["approved"] = next((a for a in approvals if a["object_id"] == f"{f['path']}@{f['sha256']}"), None)
    return {"files": files}


@router.post("/api/exporte/aggregationen")
def export_sheet(regelwerk: str = "basis"):
    def run():
        from statagent.reporting.sheet import build_sheet, write_open_data
        with connect() as conn:
            r = build_sheet(conn, regelwerk)
            o = write_open_data(conn, regelwerk)
        return {"sheet": r, "open_data": o}
    return _job(run)


@router.post("/api/exporte/ministerium")
def export_ministry():
    def run():
        from statagent.reporting.ministry import build
        with connect() as conn:
            rule = conn.execute("""SELECT rule_id, parameters FROM ops.rule WHERE action = 'ministry_delivery' AND status = 'approved'
                                   ORDER BY approved_at DESC LIMIT 1""").fetchone()
            if not rule:
                raise ValueError("Keine freigegebene Regel für die Ministeriums-Lieferung (Änderungsauftrag 3 über den Agenten erteilen "
                                 "und von einer Person freigeben lassen).")
            with conn.transaction():
                r = build(conn, rule[1])
                approver = conn.execute("SELECT approved_by FROM ops.rule WHERE rule_id = %s", (rule[0],)).fetchone()[0]
                # T8: also the generation from the Exporte page is a logged change (like the agent path in coordinator.execute_approved)
                conn.execute("INSERT INTO ops.change_log (instruction, change, object, approved_by) VALUES (%s, %s, %s, %s)",
                             ("Ministeriums-Lieferung erzeugen (Seite Exporte)",
                              f"Ministeriums-Lieferung {r['path']} erzeugt nach {rule[0]}: {r['persons']} Personen, SHA-256 {r['sha256'][:16]}… – "
                              "wartet auf Freigabe der Lieferung", f"delivery:{r['path']}", approver))
            return r
    return _job(run)


class DeliveryApproval(BaseModel):
    path: str
    person: str
    comment: str | None = None


@router.post("/api/exporte/freigeben")
def approve_delivery(a: DeliveryApproval):
    from statagent.core import change_log
    from statagent.core.rules import valid_person
    path = (BASE_DIR / a.path).resolve()
    if not path.is_file() or ABGABE.resolve() not in path.parents:
        raise HTTPException(404, "Datei nicht gefunden")
    try:
        person = valid_person(a.person)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    rel = path.relative_to(BASE_DIR).as_posix()
    with connect() as conn:
        with conn.transaction():
            conn.execute("""INSERT INTO ops.approval (object_type, object_id, decision, person, comment)
                            VALUES ('delivery', %s, 'approved', %s, %s)""", (f"{rel}@{digest}", person, a.comment))
            conn.execute("INSERT INTO ops.change_log (instruction, change, object, approved_by) VALUES (%s, %s, %s, %s)",
                         (a.comment, f"Lieferung {rel} freigegeben (SHA-256 {digest[:16]}…)", f"delivery:{rel}", person))
        change_log.export(conn)
    return {"path": rel, "sha256": digest, "person": person}


@router.get("/api/exporte/datei")
def download(path: str):
    p = (BASE_DIR / path).resolve()
    if not p.is_file() or ABGABE.resolve() not in p.parents:
        raise HTTPException(404, "Datei nicht gefunden")
    return FileResponse(p, filename=p.name)


@router.get("/api/modelle")
def model_card():
    """Model card: data, seeds, hashes, metrics per population, predictions on the real deliveries – labelled „Modell“."""
    with connect() as conn:
        cur = conn.execute("""SELECT DISTINCT ON (kind) model_id, kind, version, trained_at, data_hash, model_hash, metrics, seed, note, synth_run
                              FROM ops.model ORDER BY kind, model_id DESC""")
        cols = [c.name for c in cur.description]
        models = [dict(zip(cols, r)) for r in cur.fetchall()]
        ids = [m["model_id"] for m in models]
        cur = conn.execute("""SELECT model_id, delivery, series, expected, lower, upper, actual, flag, probability, features
                              FROM synth.prediction WHERE model_id = ANY(%s) ORDER BY model_id, series, delivery""", (ids,))
        cols = [c.name for c in cur.description]
        preds = [dict(zip(cols, [float(v) if hasattr(v, "as_integer_ratio") and not isinstance(v, (int, bool)) else v for v in r]))
                 for r in cur.fetchall()]
        runs = []
        if models:
            cur = conn.execute("SELECT seed, split, scale, months, checksum, calibration_hash FROM synth.run WHERE synth_run = %s ORDER BY seed",
                               (models[0]["synth_run"],))
            cols = [c.name for c in cur.description]
            runs = [dict(zip(cols, r)) for r in cur.fetchall()]
    return {"banner": "Modell – keine amtliche Zahl. Modelle markieren und schlagen vor; sie korrigieren keine Daten und schreiben nie in stat_*.",
            "models": models, "predictions": preds, "synthetic_runs": runs,
            "limits": ["Die Saisonmuster der synthetischen Daten sind aus denselben 24 realen Lieferungen kalibriert, auf denen bewertet wird – "
                       "die Bewertung auf den realen Daten ist für die Saisonalität nicht unabhängig.",
                       "Synthetischer Maßstab 1:20: relative Zufallsschwankungen sind größer als in den realen Daten, der Korridor ist eher zu breit.",
                       "Nur vier Fehlerarten werden gezielt eingepflanzt (DQ-01, -02, -03, -04); andere Fehler kennt der Detektor nicht.",
                       "Reale Labels: nur je eine betroffene Lieferung je Fehlerart – Präzision und Recall auf den realen Daten beruhen auf 24 Fällen."]}


@router.get("/api/pensionen")
def pensions():
    """Pension statistic: values per year, carrier/area, pension type and sex; classification with mergers; build run."""
    with connect() as conn:
        def q(sql, params=None):
            cur = conn.execute(sql, params)
            cols = [c.name for c in cur.description]
            return [dict(zip(cols, [float(v) if hasattr(v, "as_integer_ratio") and not isinstance(v, (int, bool)) else v for v in r]))
                    for r in cur.fetchall()]
        values = q("""SELECT extract(year FROM zeitraum_von)::int AS jahr, versicherungstraeger, pensionsart, geschlecht, variable, wert, status, stand
                      FROM stat_pensionen ORDER BY 1, 2, 3, 4""")
        carriers = q("SELECT * FROM klass_versicherungstraeger ORDER BY code")
        types = q("SELECT * FROM klass_pensionsart ORDER BY code")
        transitions = q("SELECT * FROM klass_uebergang WHERE klassifikation = 'klass_versicherungstraeger' ORDER BY gueltig_ab, code_alt")
        run = q("SELECT run_id, finished_at, row_count, checksum, note, status FROM ops.run WHERE kind = 'pension' ORDER BY run_id DESC LIMIT 1")
        desc = q("SELECT * FROM statistik_beschreibung WHERE statistik = 'pensionen'")
    return {"values": values, "carriers": carriers, "types": types, "transitions": transitions, "run": run[0] if run else None,
            "description": desc[0] if desc else None,
            "sql": "SELECT extract(year FROM zeitraum_von) AS jahr, versicherungstraeger, pensionsart, geschlecht, variable, wert, status, stand "
                   "FROM stat_pensionen ORDER BY 1, 2, 3, 4"}


@router.get("/api/pensionen/zellen")
def pension_cells(jahr: int, traeger: str | None = None):
    """Quellennachweis: the delivered cells (file, sheet, cell, raw text) behind the pension values of a year."""
    with connect() as conn:
        cur = conn.execute("""SELECT c.*, f.sha256 FROM store.pension_cell c JOIN roh.file f ON f.path = c.path
                              WHERE c.jahr = %s AND (%s::text IS NULL OR c.versicherungstraeger = %s OR c.versicherungstraeger LIKE %s || '-%%')
                              ORDER BY c.path, c.sheet, c.cell_ref""", (jahr, traeger, traeger, traeger or ""))
        cols = [c.name for c in cur.description]
        return {"cells": [dict(zip(cols, r)) for r in cur.fetchall()]}
