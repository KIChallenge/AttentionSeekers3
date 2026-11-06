"""Code written by the agents (T6): special evaluations (Sonderauswertungen) as readable Python files.

The agent fills a fixed, reviewed template with parameters it derived from the instruction; the file contains the
instruction, the parameters and the literal SQL, runs without a language model and refuses to run unless its exact
content (SHA-256) was approved by a named person in ops.code_proposal (T6 d, T7). Every execution is logged with
its result (T6 e) in ops.code_execution and the change log.
Start: python -m statagent code-ausfuehren C-0001 --von "Name"   (or python statagent/generated/c_0001.py --von "Name")
"""
import datetime as dt
import hashlib
import importlib.util
import json
import re

from statagent.config import BASE_DIR, connect

GEN_DIR = BASE_DIR / "statagent" / "generated"
OUT_DIR = BASE_DIR / "abgabe" / "sonderauswertungen"
GROUPS = {
    "insgesamt": ("'Insgesamt'", "Insgesamt"),
    "geschlecht": ("geschlecht", "Geschlecht"),
    "region": ("region", "Bundesland"),
    "oenace": ("oenace", "ÖNACE-Abschnitt"),
    "qualifikation": ("qualifikation", "Qualifikation"),
    "altersgruppe5": ("CASE WHEN alter = 'UNB' THEN 'unbekannt' WHEN alter::int < 15 THEN 'bis 14' WHEN alter::int >= 75 THEN '75 u. mehr' "
                      "ELSE (alter::int / 5 * 5)::text || '–' || (alter::int / 5 * 5 + 4)::text END", "Altersgruppe (5 Jahre)"),
    "altersgruppe10": ("CASE WHEN alter = 'UNB' THEN 'unbekannt' WHEN alter::int < 15 THEN 'bis 14' WHEN alter::int >= 75 THEN '75 u. mehr' "
                       "ELSE ((alter::int - 15) / 10 * 10 + 15)::text || '–' || ((alter::int - 15) / 10 * 10 + 24)::text END", "Altersgruppe (10 Jahre)"),
    "kategorie": ("CASE WHEN qualifikation LIKE 'Arbeiter%' THEN 'Arbeiter' WHEN qualifikation LIKE 'Angestellte%' THEN 'Angestellte' "
                  "ELSE qualifikation END", "Arbeiter / Angestellte / Beamte"),
    "wien_rest": ("CASE WHEN region = '9' THEN 'Wien' WHEN region = '0' THEN 'Bundesland unbekannt' ELSE 'Österreich ohne Wien' END",
                  "Wien / übriges Österreich"),
}
SAFE = re.compile(r"^[A-Za-z0-9 ._+-]{1,20}$")
FILTER_COLUMNS = {"region", "oenace", "geschlecht", "qualifikation", "alter"}
RULE_SETS = {"basis", "auftraege"}


def age_bands_sql(bounds: list[int]) -> str:
    """CASE expression for custom age bands, e.g. [15, 25, 50] → 'bis 14', '15–24', '25–49', '50 und älter'."""
    b = sorted({int(x) for x in bounds})
    if not b or any(x < 1 or x > 110 for x in b):
        raise ValueError("Altersgrenzen müssen zwischen 1 und 110 liegen")
    parts = ["WHEN alter = 'UNB' THEN 'unbekannt'", f"WHEN alter::int < {b[0]} THEN 'bis {b[0] - 1}'"]
    for lo, hi in zip(b, b[1:]):
        parts.append(f"WHEN alter::int < {hi} THEN '{lo}–{hi - 1}'")
    parts.append(f"ELSE '{b[-1]} und älter'")
    return "CASE " + " ".join(parts) + " END"


def build_sql(params: dict) -> str:
    """Literal, readable SQL for the special evaluation (validated values only)."""
    groups = params.get("group_by") or ["insgesamt"]
    for g in groups:
        if g not in GROUPS and g != "altersbaender":
            raise ValueError(f"Gliederung {g} unbekannt")
    months = params["months"]
    if params.get("rule_set", "basis") not in RULE_SETS:
        raise ValueError(f"Regelwerk {params.get('rule_set')!r} unbekannt")
    for col in list(params.get("filters", {})) + list(params.get("exclude", {})):
        if col not in FILTER_COLUMNS:
            raise ValueError(f"Spalte {col!r} nicht erlaubt")
    for v in months + [x for vals in params.get("exclude", {}).values() for x in vals] + \
            [x for vals in params.get("filters", {}).values() for x in vals]:
        if not SAFE.match(v):
            raise ValueError(f"ungültiger Wert {v!r}")
    exprs = {g: (age_bands_sql(params.get("age_bounds") or []) if g == "altersbaender" else GROUPS[g][0]) for g in groups}
    cols = ",\n       ".join(f"{exprs[g]} AS {g}" for g in groups)
    where = [f"regelwerk = '{params.get('rule_set', 'basis')}'", "variable = 'Beschaeftigungsverhaeltnisse'",
             "stand IN (" + ", ".join(f"'Lieferung {m}'" for m in months) + ")"]
    for col, vals in params.get("filters", {}).items():
        where.append(f"{col} IN (" + ", ".join(f"'{v}'" for v in vals) + ")")
    for col, vals in params.get("exclude", {}).items():
        where.append(f"{col} NOT IN (" + ", ".join(f"'{v}'" for v in vals) + ")")
    n = len(groups)
    return (f"SELECT substr(stand, 11) AS monat,\n       {cols},\n       sum(wert)::bigint AS wert\nFROM stat_beschaeftigte\n"
            f"WHERE " + "\n  AND ".join(where) + f"\nGROUP BY {', '.join(str(i + 1) for i in range(n + 1))}\n"
            f"ORDER BY {', '.join(str(i + 1) for i in range(n + 1))}")


TEMPLATE = '''"""Sonderauswertung {pid} – erzeugt vom StatAgent-Agenten „{role}“ am {created} (T6).

Anweisung (wörtlich): {instruction!r}
Was die Auswertung macht: {label}
Grundlage: stat_beschaeftigte, Regelwerk {rule_set}, {n_months} Berichtsmonate ({first} bis {last}).

Bedingungen nach Technischer Regel 6:
  (a) diese Datei ist lesbar und dokumentiert; PARAMS und SQL stehen unten im Klartext
  (b) Start per Kommandozeile:  python -m statagent code-ausfuehren {pid} --von "Name"
  (c) läuft ohne Sprachmodell, rechnet reproduzierbar (nur die SQL-Abfrage unten)
  (d) läuft nur, wenn genau dieser Inhalt (SHA-256) von einer Person freigegeben wurde (ops.code_proposal)
  (e) jede Ausführung wird mit Anweisung und Ergebnis protokolliert (ops.code_execution, ops.change_log)
"""
import sys

PROPOSAL_ID = {pid!r}
PARAMS = {params}

SQL = """
{sql}
"""


def run(conn) -> dict:
    """Executes the query and writes the result as CSV; returns the summary for the protocol."""
    from statagent.agents.codegen import write_result
    rows = conn.execute(SQL).fetchall()
    return write_result(PROPOSAL_ID, PARAMS, rows)


if __name__ == "__main__":
    from statagent.agents.codegen import execute
    person = sys.argv[sys.argv.index("--von") + 1] if "--von" in sys.argv else None
    print(execute(PROPOSAL_ID, person))
'''


def next_id(conn) -> str:
    n = conn.execute("SELECT count(*) FROM ops.code_proposal").fetchone()[0]
    return f"C-{n + 1:04d}"


def propose(conn, instruction: str, params: dict, role: str = "Reporting") -> dict:
    pid = next_id(conn)
    sql = build_sql(params)
    months = params["months"]
    text = TEMPLATE.format(pid=pid, role=role, created=dt.datetime.now().strftime("%d.%m.%Y %H:%M"), instruction=instruction,
                           label=params.get("label", "Sonderauswertung"), rule_set=params.get("rule_set", "basis"),
                           n_months=len(months), first=months[0], last=months[-1],
                           params=json.dumps(params, ensure_ascii=False, indent=4), sql=sql)
    GEN_DIR.mkdir(parents=True, exist_ok=True)
    (GEN_DIR / "__init__.py").touch()
    path = GEN_DIR / f"{pid.lower().replace('-', '_')}.py"
    path.write_bytes(text.encode("utf-8"))          # bytes: no CRLF translation on Windows, the hash pins exactly this content
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    rel = path.relative_to(BASE_DIR).as_posix()
    conn.execute("""INSERT INTO ops.code_proposal (proposal_id, created_by, instruction, path, sha256, description, params)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                 (pid, f"Agent {role}", instruction, rel, digest, params.get("label", "Sonderauswertung"), json.dumps(params, ensure_ascii=False)))
    diff = "\n".join([f"--- /dev/null", f"+++ b/{rel}", f"@@ -0,0 +1,{len(text.splitlines())} @@"] + ["+" + l for l in text.splitlines()])
    return {"proposal_id": pid, "path": rel, "sha256": digest, "content": text, "diff": diff, "sql": sql}


def decide(conn, pid: str, person: str, approve: bool, comment: str | None = None) -> str:
    from statagent.core.rules import valid_person
    person = valid_person(person)
    with conn.transaction():
        row = conn.execute("SELECT path, sha256, instruction, status FROM ops.code_proposal WHERE proposal_id = %s FOR UPDATE", (pid,)).fetchone()
        if not row:
            raise ValueError(f"Codevorschlag {pid} existiert nicht")
        path, digest, instruction, status = row
        current = hashlib.sha256((BASE_DIR / path).read_bytes()).hexdigest()
        if current != digest:
            raise ValueError(f"{path} wurde nach dem Vorschlag verändert (SHA-256 {current[:12]}… ≠ {digest[:12]}…) – Freigabe abgelehnt")
        decision = "approved" if approve else "rejected"
        conn.execute("INSERT INTO ops.approval (object_type, object_id, decision, person, comment) VALUES ('code', %s, %s, %s, %s)",
                     (f"{pid}@{digest}", decision, person, comment))
        conn.execute("UPDATE ops.code_proposal SET status = %s, approved_by = %s, approved_at = now() WHERE proposal_id = %s",
                     (decision, person, pid))
        conn.execute("INSERT INTO ops.change_log (instruction, change, object, approved_by) VALUES (%s, %s, %s, %s)",
                     (instruction, f"Code {pid} ({path}) {'freigegeben' if approve else 'abgelehnt'}, SHA-256 {digest[:16]}…", f"code:{pid}", person))
    return decision


def write_result(pid: str, params: dict, rows: list[tuple]) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    groups = params.get("group_by") or ["insgesamt"]
    header = ["monat"] + groups + ["wert"]
    lines = [";".join(header)] + [";".join(str(v) for v in r) for r in rows]
    out = OUT_DIR / f"{pid}.csv"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    totals = {}
    for r in rows:
        totals[r[0]] = totals.get(r[0], 0) + int(r[-1])
    return {"rows": len(rows), "path": out.relative_to(BASE_DIR).as_posix(), "totals": totals,
            "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
            "preview": [dict(zip(header, [int(v) if i == len(header) - 1 else v for i, v in enumerate(r)])) for r in rows[:60]]}


def guard(conn, pid: str) -> tuple:
    """T6 d: only approved code whose file is byte-identical to the approved version may run."""
    row = conn.execute("SELECT path, sha256, status, instruction, params FROM ops.code_proposal WHERE proposal_id = %s", (pid,)).fetchone()
    if not row:
        raise ValueError(f"Codevorschlag {pid} existiert nicht")
    path, digest, status, instruction, params = row
    file = BASE_DIR / path
    current = hashlib.sha256(file.read_bytes()).hexdigest() if file.is_file() else "fehlt"
    if status != "approved":
        raise PermissionError(f"{pid} darf nicht laufen: noch nicht von einer Person freigegeben (T6 d)", current)
    if current != digest:
        raise PermissionError(f"{pid} darf nicht laufen: Datei seit der Freigabe verändert", current)
    return path, digest, instruction, params


def execute(pid: str, person: str | None) -> dict:
    """Run an approved code proposal (refuses without approval or if the file changed since approval)."""
    from statagent.core.rules import valid_person
    person = valid_person(person)
    with connect() as conn:
        try:
            path, digest, instruction, params = guard(conn, pid)
        except PermissionError as exc:
            with conn.transaction():
                conn.execute("""INSERT INTO ops.code_execution (proposal_id, started_by, sha256, status, finished_at, result)
                                VALUES (%s, %s, %s, 'blocked', now(), %s)""", (pid, person, exc.args[1], json.dumps({"reason": exc.args[0]})))
            raise PermissionError(exc.args[0]) from None
        with conn.transaction():
            exec_id = conn.execute("""INSERT INTO ops.code_execution (proposal_id, started_by, sha256) VALUES (%s, %s, %s)
                                      RETURNING execution_id""", (pid, person, digest)).fetchone()[0]
        spec = importlib.util.spec_from_file_location(f"statagent.generated.{pid.lower().replace('-', '_')}", BASE_DIR / path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        try:
            result = module.run(conn)
        except Exception as exc:
            with conn.transaction():
                conn.execute("UPDATE ops.code_execution SET status = 'failed', finished_at = now(), result = %s WHERE execution_id = %s",
                             (json.dumps({"error": str(exc)}), exec_id))
            raise
        before = before_numbers(conn, params)
        result["before"] = before
        with conn.transaction():
            conn.execute("""UPDATE ops.code_execution SET status = 'done', finished_at = now(), result = %s, output_path = %s
                            WHERE execution_id = %s""", (json.dumps(result, default=str, ensure_ascii=False), result["path"], exec_id))
            conn.execute("INSERT INTO ops.change_log (instruction, change, object, approved_by) VALUES (%s, %s, %s, %s)",
                         (instruction, f"Code {pid} ausgeführt (Ausführung {exec_id}): {result['rows']} Zeilen → {result['path']}",
                          f"code-run:{pid}", person))
        return {"execution_id": exec_id, **result}


def before_numbers(conn, params: dict) -> dict:
    """Totals per month of the standard statistic for the same months (the 'before' of a live change)."""
    rows = conn.execute("""SELECT substr(stand, 11), sum(wert)::bigint FROM stat_beschaeftigte WHERE regelwerk = %s AND stand = ANY(%s)
                           GROUP BY 1 ORDER BY 1""", (params.get("rule_set", "basis"), [f"Lieferung {m}" for m in params["months"]])).fetchall()
    return {m: int(v) for m, v in rows}
