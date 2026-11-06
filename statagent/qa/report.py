"""Quality report (QB) per month and rule set, in the layout of vorlagen/qualitaetsbericht_vorlage.md (German).

All numbers come from ops.run_metric, ops.finding, ops.revision, ops.inquiry and ops.rule of the run – the text
is a fixed template filled with query results (no language model). Files: abgabe/qualitaetsberichte/<regelwerk>/.
Rückfragen are written once each to abgabe/rueckfragen/ from vorlagen/rueckfrage_vorlage.md.
"""
import datetime as dt
import hashlib

from statagent.config import BASE_DIR

OUT_DIR = BASE_DIR / "abgabe" / "qualitaetsberichte"
INQUIRY_DIR = BASE_DIR / "abgabe" / "rueckfragen"
LEVEL = {"record": "Satz", "aggregate": "Aggregat", "delivery": "Lieferung"}
CLASS = {"explained_plausible": "erklärt – plausibel", "explained_data_problem": "erklärt – Datenproblem",
         "unexplained": "nicht erklärbar"}
RULE_SET_TEXT = {"basis": "Regelwerk „basis“ – Zählregeln der Fachbeschreibung (Z1–Z8), Stichtag Monatsletzter",
                 "auftraege": "Regelwerk „auftraege“ – nach den Änderungsaufträgen 1 und 2 (ganzes Monat, Kategorien Arbeiter/Angestellte/Beamte)"}


def _fmt(n) -> str:
    return "–" if n is None else f"{int(n):,}".replace(",", ".")


def _pct(x: float) -> str:
    return f"{x:+.2%}".replace(".", ",")


def _cell(text) -> str:
    return str(text if text is not None else "").replace("|", "\\|").replace("\n", " ")


def _metrics(conn, run_id: int) -> dict:
    return {k: int(v) for k, v in conn.execute("SELECT metric, value FROM ops.run_metric WHERE run_id = %s", (run_id,))}


def render(conn, run_id: int, month: str, rule_set: str) -> str:
    run = conn.execute("SELECT rules, checksum, finished_at FROM ops.run WHERE run_id = %s", (run_id,)).fetchone()
    rules_applied, checksum, finished = run
    mt = _metrics(conn, run_id)
    file = conn.execute("SELECT path, sha256 FROM roh.file WHERE path LIKE %s", (f"lieferungen/lieferung_{month}.csv%",)).fetchone()
    approval = conn.execute("""SELECT person, decided_at FROM ops.approval WHERE object_type = 'month' AND object_id = %s
                               AND decision = 'approved' ORDER BY decided_at DESC LIMIT 1""",
                            (f"{rule_set}:{month}:run{run_id}",)).fetchone()
    whole = conn.execute(
        "SELECT 1 FROM ops.rule WHERE rule_id = ANY(%s) AND action = 'whole_month'", (rules_applied,)).fetchone() is not None
    when = "im Monat" if whole else "am Stichtag"
    prev_total = conn.execute("""SELECT sum(wert) FROM stat_beschaeftigte WHERE regelwerk = %s AND stand =
                                   'Lieferung ' || to_char(to_date(%s, 'YYYY-MM') - interval '1 month', 'YYYY-MM')""",
                              (rule_set, month)).fetchone()[0]
    as_delivered = conn.execute("SELECT value FROM store.profile WHERE delivery = %s AND metric = 'active_as_delivered'",
                                (month,)).fetchone()
    lines = [f"# Qualitätsbericht – Berichtsmonat {month}", "",
             f"{RULE_SET_TEXT.get(rule_set, rule_set)}", "",
             f"Lieferung: `{file[0].split('/')[-1] if file else month}` (SHA-256 `{file[1][:16] if file else '–'}…`) · "
             f"Lauf {run_id} · Prüfsumme `{checksum}` · erstellt am {finished:%d.%m.%Y %H:%M} · "
             + (f"freigegeben von: {approval[0]} am {approval[1]:%d.%m.%Y %H:%M}" if approval else "freigegeben von: – (noch nicht veröffentlicht)"),
             "", "## 1 Überblick", "", "| Kennzahl | Wert |", "| --- | ---: |",
             f"| gelesene Sätze | {_fmt(mt.get('rows_read'))} |",
             f"| davon gezählt {when} (ein Satz je Verhältnis) | {_fmt(mt.get('rows_counted'))} |",
             f"| nicht gezählte Sätze (kein Zeitabschnitt {when}) | {_fmt(mt.get('rows_not_counted'))} |",
             f"| ausgeschlossene oder korrigierte Sätze (weitere Sätze bereits gezählter Verhältnisse, z. B. Duplikate) | {_fmt(mt.get('rows_excluded'))} |",
             f"| Beschäftigungsverhältnisse {when} | {_fmt(mt.get('records_total'))} |",
             f"| davon aus früherer Lieferung fortgeschrieben (Annahme) | {_fmt(mt.get('records_carried'))} |",
             f"| davon „nicht zuordenbar“ | {_fmt(mt.get('records_unmapped'))} |",
             f"| nach freigegebener Regel ausgeschlossen (nicht gezählt, ausgewiesen) | {_fmt(mt.get('records_excluded_rule', 0))} |",
             f"| davon Alter unbekannt | {_fmt(mt.get('records_age_unknown'))} |",
             f"| wie geliefert (ohne Leseregeln) am Stichtag | {_fmt(as_delivered[0] if as_delivered else None)} |",
             f"| Veränderung zum Vormonat | " + (f"{'+' if mt['records_total'] >= prev_total else ''}{_fmt(mt['records_total'] - prev_total)} ({_pct(mt['records_total'] / float(prev_total) - 1)})"
                                               if prev_total else "– (erster Berichtsmonat bzw. Vormonat nicht gerechnet)") + " |",
             "",
             f"Abrechnung: gelesene Sätze = gezählte + nicht gezählte + ausgeschlossene Sätze: {_fmt(mt.get('rows_read'))} = "
             f"{_fmt(mt.get('rows_counted'))} + {_fmt(mt.get('rows_not_counted'))} + {_fmt(mt.get('rows_excluded'))} "
             + ("✓" if mt.get("rows_read") == mt.get("rows_counted", 0) + mt.get("rows_not_counted", 0) + mt.get("rows_excluded", 0) else "✗"),
             f"Jedes {when} bestehende Verhältnis der Lieferung ist genau einmal gezählt ({_fmt(mt.get('vvh_in_period'))} Verhältnisse; Prüfung im Lauf).",
             ""]

    findings = conn.execute("""SELECT check_id, problem_id, level, description, extent, example_ids, evidence_sql, classification,
                                      measure, inquiry_id FROM ops.finding WHERE run_id = %s ORDER BY finding_id""", (run_id,)).fetchall()
    lines += ["## 2 Auffälligkeiten", "",
              "| Nr. | Ebene (Satz / Aggregat / Lieferung) | Beschreibung | Umfang (Sätze, Zellen) | Beleg (Abfrage) | Einstufung | Maßnahme | Rückfrage |",
              "| --- | --- | --- | ---: | --- | --- | --- | --- |"]
    queries = []
    for i, (cid, pid, level, desc, extent, examples, sql, cls, measure, inquiry) in enumerate(findings, start=1):
        ex = f" Beispiele: VVH {', '.join(examples)}." if examples else ""
        queries.append((i, pid or cid, sql))
        lines.append(f"| {i} | {LEVEL.get(level, level)} | {_cell((pid + ': ') if pid else '')}{_cell(desc)}{_cell(ex)} | {_fmt(extent)} | "
                     f"Abfrage {i} | {CLASS.get(cls, cls)} | {_cell(measure)} | {inquiry or ''} |")
    if not findings:
        lines.append("| – | | keine Auffälligkeiten | | | | | |")
    lines += ["", "Einstufung: **erklärt – plausibel** (reale Entwicklung, mit Daten belegt) · **erklärt – Datenproblem** "
              "(Ursache in den Daten, Maßnahme umgesetzt) · **nicht erklärbar** (an die Fachabteilung eskaliert).", ""]

    inquiry_ids = sorted({f[9] for f in findings if f[9]})
    lines += ["## 3 Rückfragen an die Fachabteilung", "",
              "| Nr. | Gestellt am | Frage (kurz) | Antwort der Fachabteilung | Umgesetzt als Regel |", "| --- | --- | --- | --- | --- |"]
    for iid in inquiry_ids:
        row = conn.execute("SELECT question, asked_on, answer, implemented_as_rule FROM ops.inquiry WHERE inquiry_id = %s", (iid,)).fetchone()
        if row:
            lines.append(f"| {iid} | {row[1] or 'vorbereitet (abgabe/rueckfragen/' + iid + '.md)'} | {_cell(row[0])} | {_cell(row[2] or 'ausstehend')} | {row[3] or '–'} |")
    if not inquiry_ids:
        lines.append("| – | | keine | | |")

    lines += ["", "## 4 Angewendete Regeln", "",
              "| Regel | Seit Berichtsmonat | Grundlage (Rückfrage, Änderungsauftrag) | freigegeben von | betroffene Sätze in diesem Monat |",
              "| --- | --- | --- | --- | ---: |"]
    rule_rows = conn.execute("""SELECT rule_id, title, problem_id, parameters, approved_by, approved_at, assumption, justification, action
                                FROM ops.rule WHERE rule_id = ANY(%s) ORDER BY rule_id""", (rules_applied,)).fetchall()
    assumptions = []
    for rid, title, pid, params, by, at, assumption, justification, action in rule_rows:
        if action == "swap_columns":
            n = conn.execute("SELECT count(*) FROM store.segment WHERE delivery = %s AND %s = ANY(rules)", (month, rid)).fetchone()[0]
        elif action == "count_duplicates_once":
            n = conn.execute("SELECT count(*) FROM store.segment WHERE delivery = %s AND copy_no > 1", (month,)).fetchone()[0]
        elif action in ("trim_overlap", "close_gap"):
            n = conn.execute("SELECT count(*) FROM store.segment WHERE delivery = %s AND %s = ANY(rules)", (month, rid)).fetchone()[0]
        else:
            n = conn.execute("SELECT count(*) FROM store.month_record WHERE rule_set = %s AND month = %s AND %s = ANY(rules)",
                             (rule_set, month, rid)).fetchone()[0]
        since = ", ".join((params or {}).get("deliveries", [])) or "2024-08 (ganze Reihe)"
        basis = f"{pid}: {title}" if pid else title
        lines.append(f"| {rid} | {since} | {_cell(basis)} | {by or '–'}{f', {at:%d.%m.%Y}' if at else ''} | {_fmt(n)} |")
        if assumption or justification:
            comment = conn.execute("""SELECT comment FROM ops.approval WHERE object_type = 'rule' AND object_id = %s
                                      AND decision = 'approved' ORDER BY decided_at DESC LIMIT 1""", (rid,)).fetchone()
            assumptions.append(f"- **{rid}** – Annahme: {assumption or '–'} Begründung: {justification or '–'}"
                               + (f" Anmerkung bei der Freigabe ({by}): {comment[0]}" if comment and comment[0] else ""))
    pending = conn.execute("""SELECT rule_id, title FROM ops.rule WHERE status = 'proposed' AND rule_set IN ('basis', %s)
                              ORDER BY rule_id""", (rule_set,)).fetchall()
    if assumptions:
        lines += ["", "Annahmen und Begründungen der angewendeten Regeln:", ""] + assumptions
    if pending:
        lines += ["", "Vorgeschlagene, noch nicht freigegebene Regeln (in diesem Lauf **nicht** angewendet): "
                  + "; ".join(f"{r} {t}" for r, t in pending) + "."]

    lines += ["", "## 5 Revisionsbedarf früherer Monate", "",
              "Weicht die aktuelle Lieferung für bereits veröffentlichte Monate ab, wird das hier ausgewiesen (Veröffentlichtes bleibt unverändert).", "",
              "| Berichtsmonat | veröffentlicht | laut aktueller Lieferung | Differenz | Hauptursache |", "| --- | ---: | ---: | ---: | --- |"]
    revisions = conn.execute("""SELECT month, published, current, main_cause FROM ops.revision WHERE run_id = %s ORDER BY month DESC""",
                             (run_id,)).fetchall()
    for m, pub, cur, cause in revisions:
        lines.append(f"| {m} | {_fmt(pub)} | {_fmt(cur)} | {'+' if cur - pub > 0 else ''}{_fmt(cur - pub)} | {_cell(cause)} |")
    if not revisions:
        lines.append("| – | | | | kein früherer Monat gerechnet |")

    lines += ["", "## 6 Zuordnungen und Klassifikationen", ""]
    klass = conn.execute("""SELECT run_id, checksum FROM ops.run WHERE kind = 'classification' AND status = 'done'
                            ORDER BY run_id DESC LIMIT 1""").fetchone()
    ver = "ÖNACE 2008" if month <= "2024-12" else "ÖNACE 2025"
    lines.append(f"Wirtschaftszweig nach {ver} (Abschnitte, Zählregel Z7); Bundesland des Arbeitsortes (klass_region); "
                 f"Klassifikationsstand Lauf {klass[0] if klass else '–'}, Prüfsumme `{klass[1] if klass else '–'}`.")
    mapped = conn.execute("""SELECT r, count(*) FROM store.month_record, unnest(rules) r WHERE rule_set = %s AND month = %s
                             AND r IN (SELECT rule_id FROM ops.rule WHERE action = 'source_mapping') GROUP BY 1 ORDER BY 1""",
                          (rule_set, month)).fetchall()
    for rid, n in mapped:
        lines.append(f"- Quellzuordnung nach {rid}: {_fmt(n)} Verhältnisse")
    lines.append("- alle übrigen Codes direkt laut Klassifikationsdatei (quellzuordnung_wirksam)")

    lines += ["", "## Belegabfragen", ""]
    for i, label_, sql in queries:
        lines += [f"Abfrage {i} ({label_}):", "", "```sql", sql, "```", ""]
    lines += ["---", "Synthetische Daten für die KI Challenge (Maßstab ca. 1:10) – keine amtlichen Zahlen. "
              "Erzeugt deterministisch von `python -m statagent lauf` (ohne Sprachmodell)."]
    return "\n".join(lines) + "\n"


def write_quality_report(conn, run_id: int, month: str, rule_set: str, write_file: bool = True) -> str | None:
    text = render(conn, run_id, month, rule_set)
    path = None
    if write_file:
        out = OUT_DIR / rule_set / f"QB_{month}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(text.encode("utf-8"))
        path = out.relative_to(BASE_DIR).as_posix()
        write_inquiries(conn)
    conn.execute("""INSERT INTO ops.report (kind, rule_set, month, run_id, path, content, sha256)
                    VALUES ('quality_report', %s, %s, %s, %s, %s, %s)""",
                 (rule_set, month, run_id, path, text, hashlib.sha256(text.encode()).hexdigest()))
    return path


def write_inquiries(conn) -> list[str]:
    """Rückfragen in the layout of vorlagen/rueckfrage_vorlage.md."""
    INQUIRY_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for iid, delivery, pid, question, proposal, extent, examples, sql, asked, answer in conn.execute(
            """SELECT inquiry_id, delivery, problem_id, question, proposal, extent, example_ids, evidence_sql, asked_on, answer
               FROM ops.inquiry ORDER BY inquiry_id""").fetchall():
        text = "\n".join([
            "# Rückfrage an die Fachabteilung", "",
            f"Team: AttentionSeekers3 · Nr.: {iid} · Datum: {(asked or dt.date.today()):%d.%m.%Y}", "",
            f"**Betroffene Lieferung(en):** lieferung_{delivery}", "",
            f"**Was ist aufgefallen?** ({pid}) {question}", "", "**Beleg**", "",
            "| Angabe | Wert |", "| --- | --- |",
            f"| Anzahl betroffener Sätze | {_fmt(extent)} |",
            f"| Zeitraum / ab welcher Lieferung | ab lieferung_{delivery} |",
            "| betroffene Merkmale (Bundesland, ÖNACE, Qualifikation …) | alle (gleich verteilt) |" if pid == "DQ-02" else
            ("| betroffene Merkmale (Bundesland, ÖNACE, Qualifikation …) | Qualifikation ArbeiterFD, AngestellteFD |" if pid == "DQ-04" else
             "| betroffene Merkmale (Bundesland, ÖNACE, Qualifikation …) | neue VVH derselben Person mit identischen Merkmalen |"),
            f"| Beispiel-IDs (VVH_ID, 3–5 Stück) | {', '.join(examples or [])} |", "",
            "Abfrage, mit der das nachvollzogen werden kann:", "", "```sql", sql or "", "```", "",
            f"**Unser Vorschlag zur Behandlung:** {proposal}", "",
            f"**Frage an die Fachabteilung:** {question}", "", "---",
            f"*Antwort der Fachabteilung (wird von den Mentoren ausgefüllt):* {answer or ''}", ""])
        path = INQUIRY_DIR / f"{iid}.md"
        path.write_bytes(text.encode("utf-8"))
        paths.append(path.relative_to(BASE_DIR).as_posix())
    return paths
