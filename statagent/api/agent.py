"""API routes for the chat (Fragen), the agent console and code proposals. SSE events are documented in
statagent/agents/chat.py and statagent/agents/coordinator.py."""
import hashlib
import json
import os
import queue
import threading

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from statagent.config import BASE_DIR, connect

router = APIRouter()


def _sse(fn, *args) -> StreamingResponse:
    q: queue.Queue = queue.Queue()

    def emit(kind, data):
        q.put((kind, data))

    def worker():
        try:
            fn(*args, emit=emit)
        except Exception as exc:
            q.put(("error", {"message": str(exc)}))
        finally:
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
            yield f"event: {kind}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


class Question(BaseModel):
    question: str
    user: str | None = None
    role: str | None = None
    conversation_id: str | None = None
    previous: dict | None = None
    reading: dict | None = None
    handling: dict | None = None        # {problem_id: option_id} – treatment of faulty data on a copy (work.dq_copy)
    free_text: dict | None = None       # {problem_id: text} – own idea; mapped to an option or kept as a note


@router.get("/api/fragen/vorschlaege")
def suggestions(role: str | None = None):
    from statagent.agents.chat import suggestions as get
    with connect() as conn:
        return {"suggestions": get(conn, role)}


@router.post("/api/fragen")
def ask(q: Question):
    from statagent.agents.chat import answer
    # who is logged for a question: the logged-in name, else STATAGENT_FRAGEN_PERSON from .env, else "Gast"
    # (only the answer log ops.answer – approvals always need a logged-in named person, T7)
    user = (q.user or "").strip() or os.environ.get("STATAGENT_FRAGEN_PERSON", "").strip() or "Gast"
    return _sse(lambda emit: answer(q.question, user, q.role, q.conversation_id, q.previous, q.reading, emit=emit,
                                    handling=q.handling, free_text=q.free_text))


@router.get("/api/fragen/protokoll")
def answer_log(limit: int = 100):
    with connect() as conn:
        cur = conn.execute("""SELECT answer_id, asked_at, "user", question, kind, model, claim_check, text FROM ops.answer
                              ORDER BY answer_id DESC LIMIT %s""", (limit,))
        cols = [c.name for c in cur.description]
        return {"answers": [dict(zip(cols, r)) for r in cur.fetchall()]}


class Instruction(BaseModel):
    instruction: str
    user: str | None = None
    probe: bool = False          # Probelauf: everything is rolled back, generated files are removed


@router.post("/api/agent")
def agent(i: Instruction):
    from statagent.agents.coordinator import handle
    return _sse(lambda emit: handle(i.instruction, i.user, emit=emit, dry_run=i.probe))


@router.get("/api/agent/aufgaben")
def tasks(limit: int = 50):
    with connect() as conn:
        cur = conn.execute("""SELECT task_id, created_at, "user", instruction, role, proposals, status, model, log FROM ops.agent_task
                              ORDER BY task_id DESC LIMIT %s""", (limit,))
        cols = [c.name for c in cur.description]
        return {"tasks": [dict(zip(cols, r)) for r in cur.fetchall()]}


@router.get("/api/code")
def code_list():
    with connect() as conn:
        cur = conn.execute("""SELECT p.*, (SELECT count(*) FROM ops.code_execution e WHERE e.proposal_id = p.proposal_id AND e.status = 'done')
                              AS executions FROM ops.code_proposal p ORDER BY proposal_id DESC""")
        cols = [c.name for c in cur.description]
        return {"proposals": [dict(zip(cols, r)) for r in cur.fetchall()]}


@router.get("/api/code/{pid}")
def code_detail(pid: str):
    with connect() as conn:
        cur = conn.execute("SELECT * FROM ops.code_proposal WHERE proposal_id = %s", (pid,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, f"Codevorschlag {pid} nicht gefunden")
        data = dict(zip([c.name for c in cur.description], row))
        cur = conn.execute("SELECT * FROM ops.code_execution WHERE proposal_id = %s ORDER BY execution_id DESC", (pid,))
        data["executions"] = [dict(zip([c.name for c in cur.description], r)) for r in cur.fetchall()]
    path = BASE_DIR / data["path"]
    content = path.read_text(encoding="utf-8") if path.is_file() else ""
    data["content"] = content
    data["content_sha256"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
    data["unchanged"] = data["content_sha256"] == data["sha256"]
    data["diff"] = "\n".join(["--- /dev/null", f"+++ b/{data['path']}"] + ["+" + line for line in content.splitlines()])
    return data


class Decision(BaseModel):
    person: str
    approve: bool
    comment: str | None = None


@router.post("/api/code/{pid}/entscheidung")
def code_decide(pid: str, d: Decision):
    from statagent.agents import codegen
    from statagent.core import change_log
    try:
        with connect() as conn:
            decision = codegen.decide(conn, pid, d.person, d.approve, d.comment)
            change_log.export(conn)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return {"proposal_id": pid, "decision": decision, "person": d.person.strip()}


class Person(BaseModel):
    person: str


@router.post("/api/code/{pid}/ausfuehren")
def code_run(pid: str, p: Person):
    from statagent.agents import codegen

    def job(emit):
        emit("progress", {"pct": 10, "detail": f"{pid}: Freigabe und SHA-256 werden geprüft …"})
        try:
            r = codegen.execute(pid, p.person)
        except (PermissionError, ValueError) as exc:
            emit("error", {"message": str(exc)})
            return
        emit("progress", {"pct": 100, "detail": f"{r['rows']} Zeilen → {r['path']}"})
        emit("result", r)
    return _sse(job)
