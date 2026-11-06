"""Approvals travel with the repository: abgabe/protokoll/freigaben.json (tracked) ↔ ops.approval / ops.rule (local database).

The database is not in git. So that a fresh clone computes with the same approved rules, `protokoll` writes every rule
decision (who, when, comment) together with a fingerprint of the approved rule (action + parameters). `freigaben-wiederherstellen`
re-applies a decision only if the rule in the fresh database has exactly that fingerprint – a changed rule is never approved
by restoring; it needs a new decision by a person (T7). Restored entries keep the original person and time and are logged.
"""
import hashlib
import json

from statagent.config import BASE_DIR

FILE = BASE_DIR / "abgabe" / "protokoll" / "freigaben.json"


def fingerprint(action: str, parameters) -> str:
    return hashlib.sha256(json.dumps({"action": action, "parameters": parameters or {}}, sort_keys=True).encode()).hexdigest()


def export(conn) -> int:
    rows = conn.execute("""SELECT a.object_id, a.decision, a.person, a.decided_at, a.comment, r.action, r.parameters
                           FROM ops.approval a JOIN ops.rule r ON r.rule_id = a.object_id
                           WHERE a.object_type = 'rule' ORDER BY a.decided_at""").fetchall()
    data = [{"rule_id": rid, "decision": d, "person": p, "decided_at": at.isoformat(), "comment": c,
             "fingerprint": fingerprint(action, params)} for rid, d, p, at, c, action, params in rows]
    FILE.parent.mkdir(exist_ok=True)
    FILE.write_bytes((json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    return len(data)


def restore(conn) -> list[str]:
    if not FILE.exists():
        return []
    out = []
    with conn.transaction():
        for e in json.loads(FILE.read_text(encoding="utf-8")):
            row = conn.execute("SELECT status, action, parameters FROM ops.rule WHERE rule_id = %s", (e["rule_id"],)).fetchone()
            if not row:
                out.append(f"{e['rule_id']}: Regel nicht vorhanden – übersprungen")
                continue
            if row[0] != "proposed":
                continue                                   # already decided in this database
            if fingerprint(row[1], row[2]) != e["fingerprint"]:
                out.append(f"{e['rule_id']}: Regel hat sich seit der Freigabe geändert – NICHT wiederhergestellt, neue Freigabe nötig")
                continue
            conn.execute("""INSERT INTO ops.approval (object_type, object_id, decision, person, decided_at, comment)
                            VALUES ('rule', %s, %s, %s, %s, %s)""", (e["rule_id"], e["decision"], e["person"], e["decided_at"], e["comment"]))
            conn.execute("UPDATE ops.rule SET status = %s, approved_by = %s, approved_at = %s WHERE rule_id = %s",
                         (e["decision"], e["person"], e["decided_at"], e["rule_id"]))
            conn.execute("INSERT INTO ops.change_log (instruction, change, object, approved_by) VALUES (%s, %s, %s, %s)",
                         (e["comment"], f"Entscheidung zu {e['rule_id']} aus abgabe/protokoll/freigaben.json wiederhergestellt "
                                        f"(ursprünglich {e['decided_at'][:16]})", f"rule:{e['rule_id']}", e["person"]))
            out.append(f"{e['rule_id']}: {e['decision']} von {e['person']} ({e['decided_at'][:16]}) wiederhergestellt")
    return out
