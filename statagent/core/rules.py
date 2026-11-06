"""Rules as data (T3) and their approval by a named person (T7), with a change-log entry (T8)."""
from statagent.core.labels import DECISION

import re

PLACEHOLDER_NAMES = {"team", "admin", "agent", "statagent", "system", "user", "test", "ki", "ai", "llm", "claude", "bot",
                     "tester", "probe", "demo", "dummy", "gast", "guest", "beispiel", "example", "anonym", "anonymous"}


def valid_person(person: str | None) -> str:
    """A named human approver (T7): at least 3 characters, no placeholder or machine name."""
    name = (person or "").strip()
    # names the team listed in .env (STATAGENT_USERS) are real persons, even if a word looks like a placeholder (e.g. „Test User“)
    import os
    allowed = {n.strip().lower() for n in os.environ.get("STATAGENT_USERS", "").split(",") if n.strip()}
    if name.lower() in allowed:
        return name
    words = set(re.split(r"[^\wäöüß]+", name.lower())) - {""}
    # also "Test User", "Probe Tester", "Demo-Person": any placeholder word makes it a test name, not a person (T7)
    if len(name) <= 2 or name.lower() in PLACEHOLDER_NAMES or words & PLACEHOLDER_NAMES or "agent" in name.lower():
        raise ValueError(f"Freigabe braucht den Namen einer Person, nicht „{name}“ (T7)")
    return name


def list_rules(conn) -> list[tuple]:
    return conn.execute("""
        SELECT rule_id, problem_id, status, title, approved_by, approved_at
        FROM ops.rule ORDER BY rule_id""").fetchall()


def rule_details(conn, rule_id: str) -> dict | None:
    cur = conn.execute("SELECT * FROM ops.rule WHERE rule_id = %s", (rule_id,))
    row = cur.fetchone()
    return dict(zip([c.name for c in cur.description], row)) if row else None


def decide(conn, rule_id: str, person: str, approve: bool, comment: str | None = None) -> str:
    """Approve or reject a rule; returns the decision. The person must be a real name (DB constraint
    rejects 'Team' etc.). The change-log text is German because it is shown in the protocol."""
    decision = "approved" if approve else "rejected"
    person = valid_person(person)
    with conn.transaction():
        row = conn.execute("SELECT title FROM ops.rule WHERE rule_id = %s FOR UPDATE", (rule_id,)).fetchone()
        if row is None:
            raise ValueError(f"Regel {rule_id} existiert nicht")
        conn.execute("""INSERT INTO ops.approval (object_type, object_id, decision, person, comment)
                        VALUES ('rule', %s, %s, %s, %s)""", (rule_id, decision, person.strip(), comment))
        conn.execute("""UPDATE ops.rule SET status = %s, approved_by = %s, approved_at = now()
                        WHERE rule_id = %s""", (decision, person.strip(), rule_id))
        conn.execute("""INSERT INTO ops.change_log (instruction, change, object, approved_by)
                        VALUES (%s, %s, %s, %s)""",
                     (comment, f"Regel {rule_id} {DECISION[decision]}: {row[0]}", f"rule:{rule_id}", person.strip()))
    return decision
