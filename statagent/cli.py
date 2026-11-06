"""Command line: python -m statagent <Befehl>.

The console is a user interface, so command names, help texts and output are German (product principle:
English code, German surface). Function names are English; the German command name is set explicitly.
"""
import sys

import typer

# Piped output on Windows uses cp1252: replace characters it cannot encode (e.g. '→') instead of failing.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(errors="replace")

app = typer.Typer(help="StatAgent – deterministische Statistikproduktion (KI Challenge 2026, Use Case 3).",
                  no_args_is_help=True)


@app.command("migrieren")
def migrate_schema():
    """Datenbankschema anlegen/aktualisieren (geliefertes 01_schema.sql einmalig, dann sql/*.sql)."""
    from statagent.config import connect
    from statagent.migration import migrate
    with connect(autocommit=True) as conn:
        for name in migrate(conn):
            typer.echo(f"angewendet: {name}")


@app.command("laden")
def load_files(neu: bool = typer.Option(False, "--neu", help="Alle Dateien neu laden, auch unveränderte.")):
    """Alle Paketdateien unverändert in die Datenbank laden (Lieferungen, Klassifikationen, Pensionen, …)."""
    from statagent.etl.load import load
    load(force=neu)


@app.command("pruefen")
def verify_files():
    """Prüfen, dass keine Paketdatei seit dem Laden verändert wurde und alle Lieferungszeilen vorhanden sind."""
    from statagent.etl.load import verify
    raise typer.Exit(code=0 if verify() else 1)


@app.command("bestand")
def build_store(lieferung: str = typer.Option(None, help="Nur diese Lieferung (JJJJ-MM); Standard: alle."),
                vorschau: str = typer.Option(None, help="Vorgeschlagene Regeln (kommagetrennt) zur Vorschau; wird zurückgerollt.")):
    """Versionierten Bestand mit allen freigegebenen Leseregeln aufbauen und das Lieferungsprofil ausgeben."""
    from statagent.etl.store import build_store as run, profile_table
    rules = tuple(r.strip() for r in vorschau.split(",")) if vorschau else ()
    typer.echo(profile_table(run(lieferung, rules)))


@app.command("profil")
def show_profile():
    """Gespeichertes Lieferungsprofil ausgeben (Matrix aus Problems.md §2.1)."""
    from statagent.config import connect
    from statagent.etl.store import profile_table, stored_profile
    with connect() as conn:
        typer.echo(profile_table(stored_profile(conn)))


@app.command("klassifikation")
def build_classifications(nur_pruefen: bool = typer.Option(False, "--nur-pruefen",
                                                           help="Nur die gelieferten Codes gegen die vorhandenen Zuordnungen prüfen.")):
    """Alle klass_-Tabellen, Übergänge und Quellzuordnungen aus den Paketdateien aufbauen und die gelieferten Codes prüfen."""
    from statagent.etl.classification import build_classifications as run
    typer.echo(run(nur_pruefen))


@app.command("erklaeren")
def explain_code(klassifikation: str = typer.Argument(..., help="region | oenace | geschlecht | qualifikation | alter"),
                 code: str = typer.Argument(..., help="Code, z. B. 62280, J, 'C 10.71', UNB"),
                 version: str = typer.Option(None, help="Version, z. B. 2008, 2025, 'Stand 2025-01-01'; Standard: alle")):
    """Einen Klassifikationscode erklären: Bezeichnung, Ebene, Gültigkeit, Hierarchie, Quellzuordnungen, Übergänge."""
    from statagent.config import connect
    from statagent.reporting.explain import explain
    with connect() as conn:
        typer.echo(explain(conn, klassifikation, code, version))


@app.command("regeln")
def list_rules(regel: str = typer.Argument(None, help="Details zu einer Regel anzeigen.")):
    """Alle Regeln mit Status auflisten oder eine Regel im Detail anzeigen."""
    from statagent.config import connect
    from statagent.core import rules
    from statagent.core.labels import RULE_STATUS, label
    with connect() as conn:
        if regel:
            details = rules.rule_details(conn, regel) or {"fehler": f"Regel {regel} existiert nicht"}
            for key, value in details.items():
                typer.echo(f"{key:16} {label(RULE_STATUS, value) if key == 'status' else value}")
            return
        for rule_id, problem, status, title, by, at in rules.list_rules(conn):
            approval = f" – {by}, {at:%Y-%m-%d %H:%M}" if by else ""
            typer.echo(f"{rule_id:8} {problem or '':6} {label(RULE_STATUS, status):13} {title}{approval}")


def _decide(rule_id: str, person: str, comment: str | None, approve: bool):
    from statagent.config import connect
    from statagent.core import rules
    from statagent.core.labels import DECISION
    with connect() as conn:
        typer.echo(f"{rule_id}: {DECISION[rules.decide(conn, rule_id, person, approve, comment)]} von {person}")
        action = (rules.rule_details(conn, rule_id) or {}).get("action")
    rebuild = ("Klassifikationen neu aufbauen (python -m statagent klassifikation)" if action == "source_mapping"
               else "Bestand neu aufbauen (python -m statagent bestand)")
    typer.echo(f"Als Nächstes: {rebuild} und das Protokoll für den Commit exportieren (python -m statagent protokoll)")


@app.command("freigeben")
def approve_rule(regel: str, von: str = typer.Option(..., help="Vollständiger Name der freigebenden Person (kein „Team“)."),
                 kommentar: str = typer.Option(None, help="Anweisung; erscheint im Protokoll und in der Commit-Nachricht.")):
    """Eine vorgeschlagene Regel freigeben (mit Name und Zeitpunkt protokolliert)."""
    _decide(regel, von, kommentar, True)


@app.command("ablehnen")
def reject_rule(regel: str, von: str = typer.Option(..., help="Vollständiger Name der entscheidenden Person."),
                kommentar: str = typer.Option(None)):
    """Eine vorgeschlagene Regel ablehnen (mit Name und Zeitpunkt protokolliert)."""
    _decide(regel, von, kommentar, False)


def _print_run(r: dict):
    m = r["metrics"]
    typer.echo(f"Lauf {r['run_id']} · {r['month']} · Regelwerk {r['rule_set']} · Regeln {', '.join(r['rules']) or 'keine'}")
    typer.echo(f"  gezählt {m['records_total']:,} (davon fortgeschrieben {m['records_carried']:,}, nicht zuordenbar "
               f"{m['records_unmapped']:,}) · gelesen {m['rows_read']:,} = {m['rows_counted']:,} + {m['rows_not_counted']:,} "
               f"+ {m['rows_excluded']:,}".replace(",", "."))
    typer.echo(f"  Prüfsumme {r['checksum']} · {r['findings']} Auffälligkeiten · QB {r['report'] or '(Vorschau, nicht geschrieben)'}"
               + (" · veröffentlicht (unverändert)" if r["published"] else ""))


@app.command("lauf")
def run_month(lieferung: str = typer.Option(..., help="Berichtsmonat JJJJ-MM, z. B. 2025-03."),
              regelwerk: str = typer.Option("basis", help="basis (Fachbeschreibung) oder auftraege (nach den Änderungsaufträgen)."),
              vorschau: str = typer.Option(None, help="Vorgeschlagene Regeln (kommagetrennt) zur Vorschau; wird zurückgerollt.")):
    """Monatslauf: genau eine Lieferung nach den freigegebenen Regeln (Ergebnis, Prüfungen, Qualitätsbericht)."""
    from statagent.qa.run import run
    rules = tuple(r.strip() for r in vorschau.split(",")) if vorschau else ()
    _print_run(run(lieferung, regelwerk, rules))


@app.command("gesamtlauf")
def run_all_months(regelwerk: str = typer.Option("basis", help="basis oder auftraege.")):
    """Gesamtlauf = 24 Einzelläufe in zeitlicher Reihenfolge 2024-08 … 2026-07."""
    from statagent.qa.run import run_all
    for r in run_all(regelwerk):
        _print_run(r)


@app.command("veroeffentlichen")
def publish_months(von: str = typer.Option(..., help="Name der freigebenden Person (kein „Team“)."),
                   regelwerk: str = typer.Option("basis"), lieferung: str = typer.Option(None, help="Nur dieser Monat; Standard: alle vorläufigen."),
                   kommentar: str = typer.Option(None)):
    """Fertige Monate freigeben und veröffentlichen (Status endgültig; danach unveränderlich, Zählregel Z4)."""
    from statagent.qa.run import publish
    months = publish(von, regelwerk, lieferung, kommentar)
    typer.echo(f"{len(months)} Monate veröffentlicht ({regelwerk}) von {von}: {', '.join(months) or '–'}")


@app.command("kalibrierung")
def calibration(regelwerk: str = typer.Option("basis"),
                vorschau: str = typer.Option(None, help="Vorgeschlagene Regeln für einen Vorschau-Lauf 2024-08 (zurückgerollt).")):
    """Kalibrierungstest: alle Zellen des Beispielberichts 08/2024 gegen stat_beschaeftigte."""
    from statagent.config import connect
    from statagent.qa.calibration import MONTH, calibrate, status, write_report
    from statagent.qa.run import run_month
    with connect() as conn:
        if vorschau:
            with conn.transaction(force_rollback=True):
                run_month(conn, MONTH, regelwerk, tuple(r.strip() for r in vorschau.split(",")))
                result = calibrate(conn, regelwerk)
            typer.echo(f"Vorschau mit {vorschau} (zurückgerollt, Bericht nicht geschrieben)")
            path = "–"
        else:
            result = calibrate(conn, regelwerk)
            preview, extra = None, ()
            pending = [r for (r,) in conn.execute("SELECT rule_id FROM ops.rule WHERE rule_id = 'R-DQ05' AND status = 'proposed'").fetchall()]
            if pending and result["mismatches"]:
                extra = tuple(pending)
                with conn.transaction(force_rollback=True):
                    run_month(conn, MONTH, regelwerk, extra)
                    preview = calibrate(conn, regelwerk)
                typer.echo(f"Vorschau mit {', '.join(extra)}: {len(preview['mismatches'])} Abweichungen")
            path = write_report(conn, result, preview, extra)
    typer.echo(f"{result['cells']} Zellen verglichen, {len(result['mismatches'])} Abweichungen → {status(result).upper()} ({path})")
    if result.get("example_reading"):
        er = result["example_reading"]
        typer.echo(f"  Lesart des Beispielberichts für Geburtsmonat 13 ({er['records']} Verhältnisse): {er['mismatches']} Abweichungen")
    for tab, cell, exp, act, what in result["mismatches"][:15]:
        typer.echo(f"  {tab} {cell}: Beispielbericht {exp}, StatAgent {act} ({what})")
    raise typer.Exit(code=0 if (result["ok"] or result.get("explained")) else 1)


@app.command("aggregationen")
def export_sheet(regelwerk: str = typer.Option("basis", help="basis oder auftraege.")):
    """Aggregations-Sheet in die Vorlage schreiben (abgabe/aggregationen_<regelwerk>.xlsx) und das Open-Data-File."""
    from statagent.config import connect
    from statagent.reporting.sheet import build_sheet, write_open_data
    with connect() as conn:
        r = build_sheet(conn, regelwerk)
        o = write_open_data(conn, regelwerk)
    typer.echo(f"{r['path']}: {r['months']} Monate, {r['checked']} Blatt-Monate geprüft (Summen = stat_beschaeftigte), SHA-256 {r['sha256'][:16]}…")
    typer.echo(f"{o['path']}: {o['rows']:,} Zeilen (Open-Data-File), SHA-256 {o['sha256'][:16]}…".replace(",", "."))


@app.command("ministerium")
def export_ministry(vorschau: bool = typer.Option(False, "--vorschau", help="Ohne freigegebene Regel mit Standardparametern nach exports/ (nicht zur Abgabe).")):
    """Ministeriums-Lieferung (Änderungsauftrag 3) nach der freigegebenen Regel erzeugen: abgabe/ministerium_JJJJ-MM.csv."""
    from statagent.config import BASE_DIR, connect
    from statagent.reporting.ministry import build
    with connect() as conn:
        rule = conn.execute("""SELECT rule_id, parameters FROM ops.rule WHERE action = 'ministry_delivery' AND status = 'approved'
                               ORDER BY approved_at DESC LIMIT 1""").fetchone()
        if not rule and not vorschau:
            typer.echo("Keine freigegebene Regel für die Ministeriums-Lieferung (Aktion ministry_delivery). Auftrag über den Agenten "
                       "erteilen und von einer Person freigeben lassen – oder --vorschau.")
            raise typer.Exit(1)
        r = build(conn, rule[1] if rule else None, None if rule else BASE_DIR / "exports")
    typer.echo(f"{r['path']}: {r['persons']:,} Personen, Tage {r['min_days_found']}–{r['max_days_found']}, GEBURTSJAHR unbekannt "
               f"{r['unknown_birth_year']}, Duplikate {r['duplicates']}, sortiert {'ja' if r['sorted'] else 'NEIN'}, SHA-256 {r['sha256'][:16]}…".replace(",", "."))
    for d in r["plan"]:
        typer.echo(f"  Tage {d['month']} aus Lieferung {d['delivery']}")


@app.command("lieferung-freigeben")
def approve_delivery(datei: str = typer.Argument(..., help="Pfad der Lieferung, z. B. abgabe/ministerium_2026-07.csv"),
                     von: str = typer.Option(..., help="Name der freigebenden Person (kein „Team“)."),
                     kommentar: str = typer.Option(None)):
    """Eine erzeugte Lieferung (z. B. an das Ministerium) mit Name, Zeitpunkt und SHA-256 freigeben (T7)."""
    import hashlib
    from statagent.config import BASE_DIR, connect
    from statagent.core.rules import valid_person
    path = (BASE_DIR / datei).resolve()
    if not path.is_file() or BASE_DIR not in path.parents:
        typer.echo(f"Datei {datei} nicht gefunden"); raise typer.Exit(1)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    person = valid_person(von)
    rel = path.relative_to(BASE_DIR).as_posix()
    with connect() as conn, conn.transaction():
        conn.execute("""INSERT INTO ops.approval (object_type, object_id, decision, person, comment)
                        VALUES ('delivery', %s, 'approved', %s, %s)""", (f"{rel}@{digest}", person, kommentar))
        conn.execute("INSERT INTO ops.change_log (instruction, change, object, approved_by) VALUES (%s, %s, %s, %s)",
                     (kommentar, f"Lieferung {rel} freigegeben (SHA-256 {digest[:16]}…)", f"delivery:{rel}", person))
    typer.echo(f"{rel} freigegeben von {person} (SHA-256 {digest})")


def _print_event(kind: str, data: dict):
    if kind == "step":
        typer.echo(f"[{data['role']}] {data['text']}")
    elif kind == "proposal":
        typer.echo(f"\nVORSCHLAG {data['id']} ({data['kind']}): {data['title']}\n{data.get('description', '')}\n")
        typer.echo(data.get("diff", ""))
        for ba in data.get("before_after") or []:
            typer.echo(f"  {ba['label']}: vorher {ba.get('before', '–')} → nachher {ba.get('after', '–')}")
    elif kind == "before_after":
        typer.echo(f"  {data['label']}: vorher {data.get('before')} → nachher {data.get('after')}")
    elif kind == "text":
        typer.echo(data["markdown"])
    elif kind == "card":
        typer.echo(f"\n{data['title']}\n{data['definition']}")
        for k in data.get("kpis", []):
            typer.echo(f"  {k['label']}: {k['value']}")
        typer.echo(f"  Prüfung: {data['claim_check']['numbers_checked']} Zahlen geprüft, "
                   f"{'bestanden' if data['claim_check']['passed'] else 'NICHT bestanden'}")
        typer.echo("SQL:\n" + data["sql"])
    elif kind in ("clarification",):
        typer.echo(data["question"])
        for o in data["options"]:
            typer.echo(f"  ({o['id']}) {o['label']}: {o['definition']}")
    elif kind in ("abstention", "error"):
        typer.echo(f"{data.get('kind', 'Fehler')}: {data.get('reason') or data.get('message')}")


@app.command("agent")
def agent_instruction(anweisung: str = typer.Argument(..., help="Anweisung in Sprache, z. B. „Setze Änderungsauftrag 2 um“."),
                      von: str = typer.Option(None, help="Name der Person, die die Anweisung gibt."),
                      probe: bool = typer.Option(False, "--probe", help="Probelauf: alles wird zurückgerollt.")):
    """Anweisung an den Koordinator-Agenten: er verteilt an die Rolle, die einen Vorschlag zur Freigabe vorbereitet."""
    from statagent.agents.coordinator import handle
    handle(anweisung, von, emit=_print_event, dry_run=probe)


@app.command("frage")
def ask_question(frage: str = typer.Argument(...), lesart: str = typer.Option(None, help="Lesart bei Rückfrage, z. B. fluktuation=c")):
    """Frage an die Daten (Antwort aus der Datenbank mit Abfrage, Definition und Prüfung jeder Zahl)."""
    from statagent.agents.chat import answer
    reading = dict([lesart.split("=", 1)]) if lesart else None
    answer(frage, None, None, "cli", reading=reading, emit=_print_event)


@app.command("code-freigeben")
def approve_code(vorschlag: str, von: str = typer.Option(...), kommentar: str = typer.Option(None)):
    """Vom Agenten erzeugten Code freigeben (T6 d: vor der ersten Ausführung; der Inhalt wird per SHA-256 festgehalten)."""
    from statagent.agents import codegen
    from statagent.config import connect
    with connect() as conn:
        typer.echo(f"{vorschlag}: {codegen.decide(conn, vorschlag, von, True, kommentar)} von {von}")


@app.command("code-ablehnen")
def reject_code(vorschlag: str, von: str = typer.Option(...), kommentar: str = typer.Option(None)):
    """Vom Agenten erzeugten Code ablehnen."""
    from statagent.agents import codegen
    from statagent.config import connect
    with connect() as conn:
        typer.echo(f"{vorschlag}: {codegen.decide(conn, vorschlag, von, False, kommentar)} von {von}")


@app.command("code-ausfuehren")
def run_code(vorschlag: str, von: str = typer.Option(..., help="Person, die die Ausführung startet.")):
    """Freigegebenen Code ausführen (verweigert ohne Freigabe oder bei verändertem Inhalt); Ergebnis wird protokolliert."""
    from statagent.agents import codegen
    r = codegen.execute(vorschlag, von)
    typer.echo(f"Ausführung {r['execution_id']}: {r['rows']} Zeilen → {r['path']}")
    for m, v in list(r["totals"].items())[-3:]:
        typer.echo(f"  {m}: vorher {r['before'].get(m)} → nachher {v}")


@app.command("modelle")
def train_models(massstab: float = typer.Option(0.05, help="Anteil des realen Bestands je synthetischem Lauf (0.05 = 1:20).")):
    """Synthetische Lieferungen erzeugen, Fehlerdetektor und Erwartungskorridor trainieren und ehrlich bewerten (Modell, keine amtliche Zahl)."""
    from statagent.ml.models import train_all
    r = train_all(massstab)
    m = r["metrics"]
    typer.echo(f"Synthetischer Lauf {r['synth_run']}, Kalibrierung {r['calibration_hash'][:16]}…, Modelle {r['models']}")
    for pop, per in m["detector"].items():
        typer.echo(f"Detektor – {pop}: " + "; ".join(f"{pid} P={v['precision']} R={v['recall']} (TP {v['tp']}, FP {v['fp']}, FN {v['fn']})"
                                                     for pid, v in per.items()))
    c = m["corridor"]
    typer.echo(f"Korridor – synthetischer Test: Abdeckung {c['synthetic_test_coverage']} (Soll {c['nominal_coverage']}), "
               f"erkannt {c['synthetic_detection']}")
    typer.echo("Korridor – reale Lieferungen, außerhalb: " + ", ".join(f"{f['series']} {f['delivery']}" for f in c["real_flags"]))


@app.command("pensionen")
def build_pensions():
    """Pensionsstatistik aus den Trägermeldungen aufbauen (7 Formate, Summen über alle Träger, Summenprüfungen)."""
    from statagent.etl.pensions import build, write_report
    r = build()
    typer.echo(f"Prüfbericht: {write_report(r)}")
    typer.echo(f"Lauf {r['run_id']}: {r['files']} Dateien, {r['cells']} Zellen, {r['rows']} Zeilen in stat_pensionen, "
               f"{r['sum_checks']} Summenprüfungen bestanden, Prüfsumme {r['checksum']}")
    for f, fmt in sorted(r["formats"].items()):
        typer.echo(f"  {fmt:14} {f}")
    typer.echo("Sprünge > 25 % gegenüber dem Vorjahr (zu erklären):")
    for t, a, g, v, y, before, after in r["jumps"]:
        typer.echo(f"  {y} {t} {a} {g} {v}: {int(before)} → {int(after)}")


@app.command("sichern")
def db_backup(ziel: str = typer.Option(None, help="Zieldatei (Standard: sicherung/statistik_<Zeit>.dump).")):
    """Ganze Datenbank als komprimierte Sicherung (pg_dump) mit SHA-256 – zum Weitergeben außerhalb von git."""
    from pathlib import Path
    from statagent.core.backup import backup
    r = backup(Path(ziel) if ziel else None)
    typer.echo(f"Sicherung {r['path']} ({r['bytes'] / 1e9:.2f} GB), SHA-256 {r['sha256']}")


@app.command("wiederherstellen")
def db_restore(datei: str = typer.Argument(..., help="Sicherungsdatei (.dump) aus `sichern`."),
               ja: bool = typer.Option(False, "--ja", help="Bestätigung: ersetzt den Inhalt der konfigurierten Datenbank.")):
    """Sicherung in die konfigurierte Datenbank einspielen (vorher `statagent web` beenden)."""
    from pathlib import Path
    from statagent.core.backup import restore
    if not ja:
        typer.echo("Ersetzt den gesamten Inhalt der Datenbank – zum Bestätigen mit --ja aufrufen.")
        raise typer.Exit(code=2)
    r = restore(Path(datei))
    typer.echo(f"Eingespielt (SHA-256 {r['sha256'][:16]}…), {r['stands']} Stände in stat_beschaeftigte. Danach: `pruefen`.")


@app.command("geheimnisse")
def secret_scan():
    """Geheimnis-Scan über die ganze git-Historie und das Arbeitsverzeichnis (keine Schlüssel, Passwörter, SV-BOX-Zugang)."""
    from statagent.core.secrets import scan
    hits = scan()
    for name, where in hits:
        typer.echo(f"FUND {name}: {where}")
    typer.echo(f"{len(hits)} Funde" + (" – OK" if not hits else ""))
    raise typer.Exit(code=1 if hits else 0)


@app.command("freigaben-wiederherstellen")
def restore_approvals():
    """Nach einem frischen Klon: Regelentscheidungen aus protokoll/freigaben.json übernehmen (nur unveränderte Regeln)."""
    from statagent.config import connect
    from statagent.core import approvals_io
    with connect() as conn:
        lines = approvals_io.restore(conn)
    typer.echo("\n".join(lines) or "nichts wiederherzustellen")


@app.command("web")
def web(port: int = typer.Option(8000, help="Port der JSON-API (nur 127.0.0.1)."), reload: bool = typer.Option(False)):
    """JSON-API für die Weboberfläche starten (http://127.0.0.1:8000; Oberfläche: web/, pnpm dev)."""
    import uvicorn
    uvicorn.run("statagent.api.app:app", host="127.0.0.1", port=port, reload=reload)


@app.command("protokoll")
def export_change_log():
    """Änderungsprotokoll nach protokoll/protokoll.md exportieren und die Commit-Nachricht vorschlagen (T8)."""
    from statagent.config import connect
    from statagent.core import change_log
    with connect() as conn:
        count = change_log.export(conn)
        from statagent.core import approvals_io
        typer.echo(f"{approvals_io.export(conn)} Regelentscheidungen nach protokoll/freigaben.json geschrieben (für frische Klone)")
        typer.echo(f"{count} Einträge nach {change_log.EXPORT_FILE.relative_to(change_log.BASE_DIR).as_posix()} geschrieben")
        message = change_log.commit_message(conn)
    if message:
        typer.echo("\nVorgeschlagene Commit-Nachricht für die letzte Änderung:\n---\n" + message + "\n---")


if __name__ == "__main__":
    app()
