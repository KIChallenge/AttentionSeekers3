"""Change-log export (T8): every change with instruction, approver and time, as a tracked file.

The file protokoll/protokoll.md (German, for the jury) is committed together with the change; the commit
message is the instruction plus the object and a line 'Freigegeben-von: <Name>' (see commit_message). The team
commits; this module never runs `git commit`. On export, entries without a commit hash are linked to the first
commit after them whose message names their object (e.g. R-DQ05, C-0001, ministerium_2026-07.csv) – read-only `git log`.
"""
import datetime as dt
import subprocess
from pathlib import Path

from statagent.config import BASE_DIR

EXPORT_FILE = BASE_DIR / "protokoll" / "protokoll.md"


def entries(conn) -> list[tuple]:
    return conn.execute("""
        SELECT log_id, logged_at, object, change, coalesce(instruction, ''), coalesce(approved_by, ''),
               coalesce(git_commit, '')
        FROM ops.change_log ORDER BY log_id""").fetchall()


def _object_key(obj: str | None) -> str | None:
    """'rule:R-DQ05' → 'R-DQ05', 'delivery:abgabe/ministerium_2026-07.csv' → 'ministerium_2026-07.csv'."""
    if not obj or ":" not in obj:
        return None
    key = obj.split(":", 1)[1]
    return key.rsplit("/", 1)[-1] or None


def link_commits(conn) -> int:
    """Fill ops.change_log.git_commit from the git history (read-only); returns the number of linked entries."""
    try:
        out = subprocess.run(["git", "log", "--reverse", "--format=%H%x1f%cI%x1f%B%x1e"], cwd=BASE_DIR, capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return 0
    commits = []
    for chunk in out.split("\x1e"):
        parts = chunk.strip("\n").split("\x1f")
        if len(parts) == 3:
            commits.append((parts[0], dt.datetime.fromisoformat(parts[1]), parts[2]))
    linked = 0
    for log_id, at, obj, *_ , commit in entries(conn):
        key = _object_key(obj)
        if commit or not key:
            continue
        for sha, when, msg in commits:
            if when >= at and key in msg and "Freigegeben-von:" in msg:
                conn.execute("UPDATE ops.change_log SET git_commit = %s WHERE log_id = %s", (sha[:12], log_id))
                linked += 1
                break
    if linked:
        conn.commit()
    return linked


def export(conn, path: Path = EXPORT_FILE) -> int:
    link_commits(conn)
    rows = entries(conn)
    lines = ["# Protokoll der Änderungen", "",
             "Automatisch erzeugt aus `ops.change_log` (`python -m statagent protokoll`). Jede Änderung an Regeln, "
             "Code oder Lieferungen mit Anweisung, freigebender Person und Zeitpunkt; Vorschläge der Agenten erscheinen ohne "
             "freigebende Person, bis eine Person entscheidet. Die Spalte Commit wird aus der git-Historie ergänzt.", "",
             "| Nr. | Zeitpunkt | Objekt | Änderung | Anweisung | Freigegeben von | Commit |",
             "| ---: | --- | --- | --- | --- | --- | --- |"]
    for no, at, obj, change, instruction, person, commit in rows:
        cells = [str(no), f"{at:%Y-%m-%d %H:%M}", obj or "", change, instruction, person, commit]
        lines.append("| " + " | ".join(c.replace("|", "\\|").replace("\n", " ") for c in cells) + " |")
    path.parent.mkdir(exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(rows)


def commit_message(conn) -> str | None:
    """Suggested message for the latest approved entry: instruction (or change), object, 'Freigegeben-von: Name'."""
    rows = [r for r in entries(conn) if r[5]]
    if not rows:
        return None
    _, _, obj, change, instruction, person, _ = rows[-1]
    key = _object_key(obj)
    return f"{instruction or change}{f' ({key})' if key and key not in (instruction or change) else ''}\n\nFreigegeben-von: {person}"
