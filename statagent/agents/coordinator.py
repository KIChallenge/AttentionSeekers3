"""Koordination + four role agents (task step 5, T5–T8).

One entry point receives a natural-language instruction (German), routes it to the responsible role and lets that
role prepare the change – never activate it:
  Klassifikation       change order 1 (categories) → rule proposal R-A1 (action category_level)
  Datenmanagement      change order 2 (whole month) → rule proposal R-A2 (action whole_month); start runs
  Reporting            change order 3 (ministry delivery) → rule proposal R-A3 (action ministry_delivery);
                       live changes (age groups, Wien separately, without Beamte …) → generated code C-NNNN (T6)
  Qualitätssicherung   checks of a delivery (findings, assumptions, revision need)
Every proposal comes with a readable diff and before/after numbers computed by deterministic code. Rules and code
take effect only after a named person approves them (Freigaben, `freigeben … --von`, `code-freigeben … --von`).
"Umsetzen" (execute) only runs what a person has already approved. With Azure configured the model chooses the
intent and parameters (function call); offline the deterministic parser does. Every task is logged in ops.agent_task.
"""
import contextlib
import difflib
import json
from pathlib import Path

from statagent.agents import codegen, intent
from statagent.agents.llm import llm_status
from statagent.config import connect

ROLES = ("Koordination", "Datenmanagement", "Klassifikation", "Qualitätssicherung", "Reporting")
ORDER_RULES = {
    "order1": dict(rule_id="R-A1", problem_id="ÄA-1", type="mapping", action="category_level",
                   title="Änderungsauftrag 1: Beschäftigungskategorie nur noch Arbeiter, Angestellte, Beamte",
                   description="In Statistik und Aggregations-Sheet wird nicht mehr zwischen Dienstvertrag (DV) und freiem Dienstvertrag (FD) "
                               "unterschieden. klass_qualifikation erhält die eigene Version „Beschaeftigungskategorie“ mit den Codes Arbeiter, "
                               "Angestellte, Beamte (und UNB) sowie n:1-Übergänge von den fünf Qualifikationen; die Zuordnung kommt aus der Spalte "
                               "BESCHAEFTIGUNGSKATEGORIE von qualifikation.csv. Gilt rückwirkend für die ganze Zeitreihe (Regelwerk auftraege).",
                   assumption="Die Kategorie einer Qualifikation ist die Spalte BESCHAEFTIGUNGSKATEGORIE der Klassifikationsdatei.",
                   justification="aenderungsauftraege.md, Auftrag 1. Eigene Version verhindert die Kollision mit dem Qualifikationscode „Beamte“ "
                                 "(Schlüssel Version + Code); die Reihe nach den bisherigen Regeln (basis) bleibt unverändert erhalten."),
    "order2": dict(rule_id="R-A2", problem_id="ÄA-2", type="counting", action="whole_month",
                   title="Änderungsauftrag 2: ganzes Monat statt Stichtag",
                   description="Ein Verhältnis zählt im Berichtsmonat, wenn mindestens ein Zeitabschnitt mindestens einen Tag im Monat besteht "
                               "(Beginn ≤ Monatsletzter und Ende leer oder ≥ Monatserster). Jedes Verhältnis zählt genau einmal; Merkmale aus dem "
                               "letzten Zeitabschnitt im Monat; Alter am Monatsletzten; weiterhin die Lieferung des Berichtsmonats. Rückwirkend, "
                               "zusammen mit Auftrag 1 (Regelwerk auftraege, zeitraum_art „Monat“).",
                   assumption="„Letzter Zeitabschnitt“ = Abschnitt mit dem spätesten Beginn im Monat; die Leseregeln R-DQ01 ff. gelten weiter.",
                   justification="aenderungsauftraege.md, Auftrag 2. Bei Überlappungen (DQ-09) entscheidet der spätere Beginn, wie in R-DQ09."),
    "order3": dict(rule_id="R-A3", problem_id="ÄA-3", type="counting", action="ministry_delivery",
                   title="Änderungsauftrag 3: Lieferung an das Ministerium (Arbeiter in Abschnitt C, ≥ 200 Tage)",
                   description="Liste aller Personen mit mindestens 200 Kalendertagen als ArbeiterDV/ArbeiterFD im ÖNACE-Abschnitt C in den zwölf "
                               "Monaten bis einschließlich Berichtsmonat. Je Tag gilt die jüngste Lieferung, die ihn enthält (höchstens die des "
                               "Berichtsmonats); gleichzeitige Verhältnisse zählen einen Tag einmal, DV- und FD-Tage zusammen. Felder PERSON_ID; "
                               "GESCHLECHT; GEBURTSJAHR; TAGE, sortiert nach PERSON_ID.",
                   assumption="Lieferung 2025-10 ist unvollständig (DQ-02): fehlt dort ein Verhältnis vollständig, gelten für die Tage, die "
                              "2025-09 abdeckt, dessen Abschnitte. GEBURTSJAHR „Unbekannt“ bei Alter über 110 (DQ-06); bei Monat 13 (DQ-05) ist "
                              "das Jahr plausibel und wird geliefert.",
                   justification="aenderungsauftraege.md, Auftrag 3 („verarbeitet nach den selbst festgelegten Regeln“). Ohne die DQ-02-Annahme "
                                 "verlören rund 20 % der Personen die Augusttage 2025 (Anhang A Regel 1)."),
}


class Agent:
    def __init__(self, user: str | None, emit):
        self.user, self.emit, self.log = user, emit, []

    def step(self, role: str, text: str, **extra):
        self.log.append({"role": role, "text": text})
        self.emit("step", {"role": role, "text": text, **extra})


def _available(conn) -> list[str]:
    return [r[0] for r in conn.execute("SELECT lieferung FROM roh.ladeprotokoll ORDER BY 1").fetchall()]


def llm_route(text: str, available: list[str]) -> dict | None:
    if not llm_status()["configured"]:
        return None
    from statagent.agents.llm import LLMUnavailable, chat
    schema = {"type": "function", "function": {"name": "route", "description": "Zuständige Rolle und Absicht einer Anweisung.",
              "parameters": {"type": "object", "required": ["intent"], "properties": {
                  "intent": {"type": "string", "enum": ["order1", "order2", "order3", "special", "check", "run", "execute", "explain", "unknown"]},
                  "group_by": {"type": "array", "items": {"type": "string", "enum": list(codegen.GROUPS)}},
                  "exclude_qualifikation": {"type": "array", "items": {"type": "string"}},
                  "exclude_region": {"type": "array", "items": {"type": "string"}},
                  "months": {"type": "array", "items": {"type": "string"}},
                  "rule_set": {"type": "string", "enum": ["basis", "auftraege"]},
                  "report_month": {"type": "string"}, "min_days": {"type": "integer"}, "label": {"type": "string"}}}}}
    system = ("Du bist der Koordinator eines Statistikteams (Beschäftigtenstatistik). Ordne Anweisungen einer Absicht zu: order1 = DV und FD "
              "zusammen (Kategorien Arbeiter/Angestellte/Beamte), order2 = ganzes Monat statt Stichtag, order3 = Ministeriums-Lieferung, "
              "special = Sonderauswertung/Live-Änderung (Gliederung, Ausschluss), check = Qualitätsprüfung, run = Läufe starten, execute = "
              "freigegebene Änderungen umsetzen. Nenne nie Zahlen. Monate: " + f"{available[0]} bis {available[-1]}.")
    try:
        r = chat([{"role": "system", "content": system}, {"role": "user", "content": text}], tools=[schema], purpose="agent:route",
                 tool_choice={"type": "function", "function": {"name": "route"}})
    except LLMUnavailable:
        return None
    if not r["tool_calls"]:
        return None
    a = r["tool_calls"][0]["arguments"]
    base = intent.parse_instruction(text, available)
    if a.get("intent") and a["intent"] != base["intent"]:
        base["intent"] = a["intent"]
        base["role"] = {"order1": "Klassifikation", "order2": "Datenmanagement", "order3": "Reporting", "special": "Reporting",
                        "check": "Qualitätssicherung", "run": "Datenmanagement", "execute": "Koordination", "explain": "Klassifikation"}.get(a["intent"], "Koordination")
        if a["intent"] == "special":
            base["params"] = {"group_by": a.get("group_by") or ["insgesamt"], "filters": {},
                              "exclude": {k: v for k, v in (("qualifikation", a.get("exclude_qualifikation")), ("region", a.get("exclude_region"))) if v},
                              "months": a.get("months") or available, "rule_set": a.get("rule_set", "basis"), "label": a.get("label") or "Sonderauswertung"}
    base["model"] = r["model"]
    return base


def _rule_diff(before: dict | None, after: dict) -> str:
    def lines(d):
        return [f"{k}: {json.dumps(v, ensure_ascii=False, default=str)}" for k, v in (d or {}).items()]
    return "\n".join(difflib.unified_diff(lines(before), lines(after), fromfile="ops.rule (vorher)", tofile=f"ops.rule {after['rule_id']} (Vorschlag)", lineterm=""))


def propose_rule(conn, agent: Agent, key: str, role: str, params: dict, instruction: str) -> dict:
    spec = dict(ORDER_RULES[key])
    existing = conn.execute("SELECT status, parameters, approved_by FROM ops.rule WHERE rule_id = %s", (spec["rule_id"],)).fetchone()
    row = {**spec, "parameters": params, "rule_set": "auftraege", "created_by": f"Agent {role} (Anweisung von {agent.user or 'unbekannt'})"}
    if existing and existing[0] in ("approved", "proposed"):
        agent.step(role, f"{spec['rule_id']} existiert bereits ({'freigegeben von ' + existing[2] if existing[0] == 'approved' else 'vorgeschlagen, wartet auf Freigabe'}) – kein neuer Vorschlag.")
        return {"kind": "rule", "id": spec["rule_id"], "title": spec["title"], "status": existing[0], "description": spec["description"],
                "diff": _rule_diff(None, {"rule_id": spec["rule_id"], "parameters": existing[1]})}
    with conn.transaction():
        if existing:   # rejected earlier: a new proposal replaces the rejected text (the rejection stays in ops.approval)
            conn.execute("UPDATE ops.rule SET status = 'proposed', parameters = %s, approved_by = NULL, approved_at = NULL, created_by = %s, "
                         "created_at = now() WHERE rule_id = %s", (json.dumps(params), row["created_by"], spec["rule_id"]))
        else:
            conn.execute("""INSERT INTO ops.rule (rule_id, problem_id, type, title, description, assumption, justification, action, parameters,
                              rule_set, created_by) VALUES (%(rule_id)s, %(problem_id)s, %(type)s, %(title)s, %(description)s, %(assumption)s,
                              %(justification)s, %(action)s, %(parameters)s, %(rule_set)s, %(created_by)s)""",
                         {**row, "parameters": json.dumps(params, ensure_ascii=False)})
        conn.execute("INSERT INTO ops.change_log (instruction, change, object, approved_by) VALUES (%s, %s, %s, NULL)",
                     (instruction, f"Regel {spec['rule_id']} vorgeschlagen von Agent {role} (noch nicht wirksam): {spec['title']}", f"rule:{spec['rule_id']}"))
    agent.step(role, f"Regelvorschlag {spec['rule_id']} angelegt (Status: vorgeschlagen). Wirksam erst nach Freigabe durch eine Person.")
    return {"kind": "rule", "id": spec["rule_id"], "title": spec["title"], "description": spec["description"], "status": "proposed",
            "assumption": spec["assumption"], "justification": spec["justification"],
            "diff": _rule_diff(None, {k: row[k] for k in ("rule_id", "type", "title", "action", "parameters", "rule_set", "created_by")})}


def before_after_order1(conn) -> list[dict]:
    month = conn.execute("SELECT max(substr(stand, 11)) FROM stat_beschaeftigte WHERE regelwerk = 'basis'").fetchone()[0]
    rows = conn.execute("""SELECT s.qualifikation, k.attribute->>'beschaeftigungskategorie', sum(s.wert)::bigint
                           FROM stat_beschaeftigte s LEFT JOIN klass_qualifikation k ON k.version = '-' AND k.code = s.qualifikation
                           WHERE s.regelwerk = 'basis' AND s.stand = %s GROUP BY 1, 2 ORDER BY 1""", (f"Lieferung {month}",)).fetchall()
    after = {}
    for q, cat, v in rows:
        after[cat or "UNB"] = after.get(cat or "UNB", 0) + int(v)
    out = [{"label": f"{month} {q} (vorher)", "before": int(v), "after": None} for q, _, v in rows]
    out += [{"label": f"{month} {c} (nachher)", "before": None, "after": v} for c, v in after.items()]
    return out


def preview_order2(conn, agent: Agent) -> list[dict]:
    from statagent.qa.run import RunError, run_month
    month = conn.execute("SELECT max(substr(stand, 11)) FROM stat_beschaeftigte WHERE regelwerk = 'basis'").fetchone()[0]
    before = conn.execute("SELECT sum(wert)::bigint FROM stat_beschaeftigte WHERE regelwerk = 'basis' AND stand = %s",
                          (f"Lieferung {month}",)).fetchone()[0]
    agent.step("Datenmanagement", f"Vorschau: Lauf {month} mit R-A2 (wird zurückgerollt, nichts gespeichert) …")
    try:
        with conn.transaction(force_rollback=True):
            r = run_month(conn, month, "auftraege", ("R-A2",), progress=lambda s, pct, d: agent.emit("progress", {"pct": pct, "detail": d}))
    except RunError as exc:
        agent.step("Datenmanagement", f"Vorschau fehlgeschlagen: {exc}")
        return []
    after = r["metrics"]["records_total"]
    return [{"label": f"{month} Beschäftigungsverhältnisse (Stichtag → ganzes Monat)", "before": int(before), "after": int(after),
             "diff": int(after) - int(before)}]


def preview_order3(conn, agent: Agent, params: dict) -> list[dict]:
    from statagent.config import BASE_DIR
    from statagent.reporting.ministry import build
    agent.step("Reporting", f"Vorschau der Ministeriums-Lieferung {params['report_month']} (nach exports/, nicht zur Abgabe) …")
    with conn.transaction(force_rollback=True):
        r = build(conn, params, BASE_DIR / "exports")
    return [{"label": f"Personen mit ≥ {params['min_days']} Tagen ({params['report_month']})", "before": None, "after": r["persons"]},
            {"label": "GEBURTSJAHR Unbekannt", "before": None, "after": r["unknown_birth_year"]}]


def execute_approved(conn, agent: Agent, instruction: str, months: list[str] | None, commit_each: bool = False) -> list[dict]:
    """Run only what a named person has approved: classification rebuild, monthly runs, ministry file, code."""
    done = []
    approved = {r[0]: r for r in conn.execute("""SELECT rule_id, action, parameters, approved_by FROM ops.rule
                                                 WHERE rule_set = 'auftraege' AND status = 'approved'""").fetchall()}
    if not approved and not conn.execute("SELECT 1 FROM ops.code_proposal WHERE status = 'approved'").fetchone():
        agent.step("Koordination", "Nichts umzusetzen: Es gibt keine freigegebenen Aufträge oder Codevorschläge. Bitte zuerst in „Freigaben“ freigeben.")
        return done
    if "R-A1" in approved:
        has_level = conn.execute("SELECT 1 FROM klass_qualifikation WHERE version = 'Beschaeftigungskategorie' LIMIT 1").fetchone()
        if not has_level:
            agent.step("Klassifikation", "R-A1 freigegeben: Klassifikationen werden neu aufgebaut (Ebene Beschäftigungskategorie) …")
            from statagent.config import setup_logging
            from statagent.etl import classification
            with conn.transaction():
                classification.build(conn, setup_logging("klassifikation"))
            if commit_each:
                conn.commit()                    # the new classification level is kept even if a later month fails
            done.append({"step": "klassifikation", "rule": "R-A1"})
            agent.step("Klassifikation", "klass_qualifikation Version „Beschaeftigungskategorie“ angelegt (Arbeiter, Angestellte, Beamte, UNB) mit n:1-Übergängen.")
    if {"R-A1", "R-A2"} & set(approved):
        from statagent.qa.run import all_months, run_month
        months = months or all_months(conn)
        agent.step("Datenmanagement", f"Regelwerk Aufträge: {len(months)} Monatsläufe der Reihe nach ({months[0]} … {months[-1]}) …")
        # Resume after a crash or a closed tab: every month is committed on its own, so a month that already has a finished
        # auftraege run computed AFTER the latest approval of R-A1/R-A2 is kept; the series continues with the next month.
        rules_now = sorted(set(approved) & {"R-A1", "R-A2"})
        last_approval = conn.execute("SELECT max(approved_at) FROM ops.rule WHERE rule_id = ANY(%s)", (rules_now,)).fetchone()[0]
        finished = {d: rid for d, rid in conn.execute(
            """SELECT DISTINCT ON (delivery) delivery, run_id FROM ops.run
               WHERE kind = 'month' AND rule_set = 'auftraege' AND status = 'done' AND note IS NULL AND rules @> %s
                 AND finished_at > %s ORDER BY delivery, run_id DESC""", (rules_now, last_approval)).fetchall()}
        resume = 0
        while resume < len(months) and months[resume] in finished:
            resume += 1
        if resume:
            agent.step("Datenmanagement", f"Fortsetzung: {resume} Monate ({months[0]} … {months[resume - 1]}) sind bereits nach der "
                                          f"letzten Freigabe gerechnet (bis Lauf {finished[months[resume - 1]]}) – weiter ab {months[resume] if resume < len(months) else '–'}.")
        for i, m in enumerate(months):
            if i < resume:
                continue
            with conn.transaction():
                r = run_month(conn, m, "auftraege", progress=lambda s, pct, d, i=i, m=m: agent.emit(
                    "progress", {"pct": int(100 * (i + pct / 100) / len(months)), "detail": f"[{i + 1}/{len(months)}] {m}: {d}"}))
            if commit_each:
                # SW-32: store every finished month at once (the connection is not autocommit, so conn.transaction() above is only
                # a savepoint) – after a crash or a closed tab the next „Setze … um“ continues with the next month
                conn.commit()
            before = conn.execute("SELECT sum(wert)::bigint FROM stat_beschaeftigte WHERE regelwerk = 'basis' AND stand = %s", (f"Lieferung {m}",)).fetchone()[0]
            done.append({"step": "lauf", "month": m, "run_id": r["run_id"], "before": before, "after": r["metrics"]["records_total"]})
            agent.emit("before_after", {"label": f"{m}: basis (Stichtag) → auftraege", "before": before, "after": r["metrics"]["records_total"]})
        with conn.transaction():
            conn.execute("INSERT INTO ops.change_log (instruction, change, object, approved_by) VALUES (%s, %s, %s, %s)",
                         (instruction, f"Regelwerk Aufträge gerechnet ({len(months)} Monate) nach den freigegebenen Regeln "
                                       f"{', '.join(sorted(set(approved) & {'R-A1', 'R-A2'}))}", "rule_set:auftraege",
                          ", ".join(sorted({approved[r][3] for r in approved if r in ('R-A1', 'R-A2')}))))
    if "R-A3" in approved:
        from statagent.reporting.ministry import build
        agent.step("Reporting", "R-A3 freigegeben: Ministeriums-Lieferung wird erzeugt …")
        with conn.transaction():
            r = build(conn, approved["R-A3"][2])
            conn.execute("INSERT INTO ops.change_log (instruction, change, object, approved_by) VALUES (%s, %s, %s, %s)",
                         (instruction, f"Ministeriums-Lieferung {r['path']} erzeugt: {r['persons']} Personen, SHA-256 {r['sha256'][:16]}… – "
                                       "wartet auf Freigabe der Lieferung", f"delivery:{r['path']}", approved["R-A3"][3]))
        done.append({"step": "ministerium", **{k: r[k] for k in ("path", "persons", "sha256")}})
        agent.step("Reporting", f"{r['path']}: {r['persons']:,} Personen. Die Lieferung braucht noch eine Freigabe durch eine Person (Freigaben).".replace(",", "."))
    for (pid,) in conn.execute("""SELECT proposal_id FROM ops.code_proposal p WHERE status = 'approved' AND NOT EXISTS
                                  (SELECT 1 FROM ops.code_execution e WHERE e.proposal_id = p.proposal_id AND e.status = 'done')""").fetchall():
        agent.step("Reporting", f"{pid} ist freigegeben – wird ausgeführt …")
        approver = conn.execute("SELECT approved_by FROM ops.code_proposal WHERE proposal_id = %s", (pid,)).fetchone()[0]
        r = codegen.execute(pid, agent.user or approver)
        done.append({"step": "code", "proposal": pid, "path": r["path"], "before": r["before"], "after": r["totals"]})
        for m in list(r["totals"])[-3:]:
            agent.emit("before_after", {"label": f"{pid} {m}", "before": r["before"].get(m), "after": r["totals"][m]})
    return done


def handle(instruction: str, user: str | None, emit=lambda kind, data: None, dry_run: bool = False) -> dict:
    """`dry_run`: everything happens in one transaction that is rolled back (tests, rehearsals); generated files are removed."""
    instruction = (instruction or "").strip()[:2000]
    agent = Agent(user, emit)
    with connect() as conn, (conn.transaction(force_rollback=True) if dry_run else contextlib.nullcontext()):
        if dry_run:
            agent.step("Koordination", "Probelauf: alle Änderungen werden am Ende zurückgerollt.")
        available = _available(conn)
        offline = intent.parse_instruction(instruction, available)
        # carrying out approved orders is recognised deterministically – the model must not turn it into something else
        parsed = offline if offline["intent"] == "execute" else (llm_route(instruction, available) or offline)
        model = parsed.get("model") or llm_status()["mode_label"]
        with conn.transaction():
            task_id = conn.execute("""INSERT INTO ops.agent_task ("user", instruction, role, plan, model) VALUES (%s, %s, %s, %s, %s)
                                      RETURNING task_id""", (user, instruction, parsed["role"], json.dumps(parsed, ensure_ascii=False, default=str),
                                                            model)).fetchone()[0]
        agent.step("Koordination", f"Anweisung erhalten ({model}). Zuständig: {parsed['role']}.")
        proposals, result = [], {}
        it = parsed["intent"]
        if it in ("order1", "order2", "order3"):
            role = parsed["role"]
            if it == "order1":
                agent.step("Klassifikation", "Prüfe vorhandene Klassifikation: klass_qualifikation hat 5 Qualifikationen mit dem Attribut "
                                             "Beschäftigungskategorie (Arbeiter, Angestellte, Beamte) – neue Ebene als eigene Version nötig.")
            if it == "order2":
                agent.step("Datenmanagement", "Neue Zählregel als eigenes Regelwerk „Aufträge“ – die Reihe nach den bisherigen Regeln bleibt erhalten.")
            prop = propose_rule(conn, agent, it, role, parsed["params"], instruction)
            if prop.get("status") == "proposed" or prop.get("status") == "approved":
                if it == "order1":
                    prop["before_after"] = before_after_order1(conn)
                    agent.step("Reporting", "Aggregations-Sheet: Blatt „Beschaeftigungskategorie“ erhält im Regelwerk Aufträge die Zeilen "
                                            "Arbeiter, Angestellte, Beamte (reporting/sheet.py).")
                elif it == "order2":
                    prop["before_after"] = preview_order2(conn, agent)
                elif it == "order3":
                    prop["before_after"] = preview_order3(conn, agent, parsed["params"])
            proposals.append(prop)
            emit("proposal", prop)
            agent.step("Koordination", "Nächster Schritt: Freigabe durch eine Person unter „Freigaben“ (oder `python -m statagent freigeben "
                                       f"{prop['id']} --von \"Name\"`), danach „Freigegebene Aufträge umsetzen“.")
        elif it == "special":
            params = parsed["params"]
            agent.step("Reporting", f"Live-Änderung als Sonderauswertung: {params['label']}; Gliederung {', '.join(params['group_by'])}; "
                                    f"{len(params['months'])} Monat(e), Regelwerk {params['rule_set']}.")
            with conn.transaction():
                c = codegen.propose(conn, instruction, params, "Reporting")
                conn.execute("INSERT INTO ops.change_log (instruction, change, object, approved_by) VALUES (%s, %s, %s, NULL)",
                             (instruction, f"Code {c['proposal_id']} vorgeschlagen von Agent Reporting ({c['path']}), noch nicht freigegeben",
                              f"code:{c['proposal_id']}"))
            before = codegen.before_numbers(conn, params)
            prop = {"kind": "code", "id": c["proposal_id"], "title": f"Sonderauswertung {c['proposal_id']}: {params['label']}",
                    "description": f"Lesbare Datei {c['path']} (SHA-256 {c['sha256'][:16]}…), läuft ohne Sprachmodell, nur nach Freigabe.",
                    "diff": c["diff"], "sql": c["sql"], "status": "proposed",
                    "before_after": [{"label": f"{m} Insgesamt (Standardstatistik)", "before": v, "after": None} for m, v in list(before.items())[-3:]]}
            proposals.append(prop)
            emit("proposal", prop)
            agent.step("Koordination", f"Code {c['proposal_id']} wartet auf Freigabe (T6 d). Danach „Freigegebene Aufträge umsetzen“ oder "
                                       f"`python -m statagent code-ausfuehren {c['proposal_id']} --von \"Name\"`.")
        elif it == "execute" or (it == "run" and "umsetz" in instruction.lower()):
            months = intent.parse_months(intent.norm(instruction), available)[0] or None
            result["executed"] = execute_approved(conn, agent, instruction, months, commit_each=not dry_run)
        elif it == "run":
            from statagent.qa.run import run_month
            months = parsed["params"]["months"]
            agent.step("Datenmanagement", f"Starte {len(months)} Monatsläufe ({parsed['params']['rule_set']}) …")
            out = []
            for i, m in enumerate(months):
                with conn.transaction():
                    r = run_month(conn, m, parsed["params"]["rule_set"], progress=lambda s, pct, d, i=i, m=m: emit(
                        "progress", {"pct": int(100 * (i + pct / 100) / len(months)), "detail": f"[{i + 1}/{len(months)}] {m}: {d}"}))
                out.append({"month": m, "run_id": r["run_id"], "total": r["metrics"]["records_total"], "checksum": r["checksum"]})
            result["runs"] = out
            agent.step("Datenmanagement", f"{len(out)} Läufe fertig; Prüfsummen und Qualitätsberichte unter „Läufe“.")
        elif it == "check":
            m = parsed["params"]["months"][0]
            rows = conn.execute("""SELECT f.problem_id, f.description, f.classification FROM ops.finding f JOIN ops.run r USING (run_id)
                                   WHERE r.kind = 'month' AND r.status = 'done' AND r.note IS NULL AND f.delivery = %s AND f.rule_set = 'basis'
                                   AND r.run_id = (SELECT max(run_id) FROM ops.run WHERE kind = 'month' AND status = 'done' AND note IS NULL
                                                   AND delivery = %s AND rule_set = 'basis') ORDER BY f.finding_id""", (m, m)).fetchall()
            agent.step("Qualitätssicherung", f"Lieferung {m}: {len(rows)} Auffälligkeiten aus dem letzten Lauf.")
            emit("text", {"markdown": "\n".join(f"- **{p or 'Prüfung'}** – {d} *({c})*" for p, d, c in rows[:25])})
        else:
            agent.step("Koordination", "Die Anweisung lässt sich keiner Rolle eindeutig zuordnen – Rückfrage: Was soll geändert werden? "
                                       "Beispiele: „Setze Änderungsauftrag 1 um“, „Ganzes Monat statt Stichtag“, „Erzeuge die Ministeriums-Lieferung "
                                       "07/2026“, „Zeig die Beschäftigten in 5-Jahres-Altersgruppen“, „Wien gesondert ausweisen“, "
                                       "„Beamte ausschließen“, „Setze die freigegebenen Aufträge um“.")
        with conn.transaction():
            conn.execute("UPDATE ops.agent_task SET proposals = %s, status = %s, log = %s WHERE task_id = %s",
                         ([p["id"] for p in proposals], "proposed" if proposals else "done", json.dumps(agent.log, ensure_ascii=False), task_id))
    if dry_run:
        from statagent.config import BASE_DIR
        for prop in proposals:
            if prop["kind"] == "code":
                Path(BASE_DIR / "statagent" / "generated" / f"{prop['id'].lower().replace('-', '_')}.py").unlink(missing_ok=True)
    else:
        from statagent.core import change_log
        with connect() as conn:
            change_log.export(conn)
    emit("done", {"task_id": task_id, "model": model, "dry_run": dry_run})
    return {"task_id": task_id, "intent": it, "proposals": proposals, "result": result, "log": agent.log}
