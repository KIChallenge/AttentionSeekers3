"""Integration tests against the local database (skipped without one). Every test that writes runs in a transaction
that is rolled back, so the published state is never changed by tests.

Anchors: 08/2024 = 392,236 (example report); calibration 2,880 cells; reproducible checksums; nothing lost.
"""
import pytest

pytestmark = pytest.mark.integration   # fast run without the DB: pytest -m "not integration"

psycopg = pytest.importorskip("psycopg")
from statagent.config import connect  # noqa: E402


@pytest.fixture(scope="module")
def conn():
    try:
        c = connect()
    except psycopg.OperationalError:
        pytest.skip("keine Datenbank erreichbar")
    if not c.execute("SELECT count(*) FROM stat_beschaeftigte WHERE regelwerk = 'basis'").fetchone()[0]:
        pytest.skip("noch keine Monatsläufe")
    yield c
    c.close()


def test_package_rows_complete(conn):
    assert conn.execute("SELECT sum(zeilen) FROM roh.ladeprotokoll").fetchone()[0] == 10_152_292
    assert conn.execute("SELECT count(*) FROM store.segment").fetchone()[0] == 10_152_292


def test_example_report_total(conn):
    assert conn.execute("SELECT sum(wert) FROM stat_beschaeftigte WHERE regelwerk = 'basis' AND stand = 'Lieferung 2024-08'").fetchone()[0] == 392_236


def test_every_month_reconciles_and_loses_nothing(conn):
    rows = conn.execute("""SELECT r.delivery, m1.value, m2.value, m3.value, m4.value, m5.value, m6.value
                           FROM ops.run r
                           JOIN ops.run_metric m1 ON m1.run_id = r.run_id AND m1.metric = 'rows_read'
                           JOIN ops.run_metric m2 ON m2.run_id = r.run_id AND m2.metric = 'rows_counted'
                           JOIN ops.run_metric m3 ON m3.run_id = r.run_id AND m3.metric = 'rows_not_counted'
                           JOIN ops.run_metric m4 ON m4.run_id = r.run_id AND m4.metric = 'rows_excluded'
                           JOIN ops.run_metric m5 ON m5.run_id = r.run_id AND m5.metric = 'vvh_in_period'
                           JOIN ops.run_metric m6 ON m6.run_id = r.run_id AND m6.metric = 'records_delivery'
                           WHERE r.run_id IN (SELECT max(run_id) FROM ops.run WHERE kind = 'month' AND status = 'done' AND note IS NULL
                                              AND rule_set = 'basis' GROUP BY delivery)""").fetchall()
    assert len(rows) == 24
    for month, read, counted, not_counted, excluded, in_period, records in rows:
        assert read == counted + not_counted + excluded, month
        assert in_period == records, month


def test_stat_sums_equal_counted_records(conn):
    bad = conn.execute("""SELECT s.stand FROM (SELECT stand, lauf_id, sum(wert) AS w FROM stat_beschaeftigte WHERE regelwerk = 'basis'
                                               GROUP BY 1, 2) s
                          JOIN ops.run_metric m ON m.run_id = s.lauf_id AND m.metric = 'records_total' WHERE m.value <> s.w""").fetchall()
    assert bad == []


def test_rerun_gives_the_same_checksum(conn):
    from statagent.qa.run import run_month
    stored = conn.execute("""SELECT checksum FROM ops.run WHERE run_id = (SELECT max(lauf_id) FROM stat_beschaeftigte
                             WHERE regelwerk = 'basis' AND stand = 'Lieferung 2024-08')""").fetchone()[0]
    with conn.transaction(force_rollback=True):
        result = run_month(conn, "2024-08", "basis", write_files=False)
    assert result["checksum"] == stored


def test_calibration_against_example_report(conn):
    """With the proposed rule R-DQ05 (preview, rolled back) every cell matches; without it only the age table differs."""
    from statagent.qa.calibration import calibrate
    from statagent.qa.run import run_month
    approved = conn.execute("SELECT status FROM ops.rule WHERE rule_id = 'R-DQ05'").fetchone()[0] == "approved"
    with conn.transaction(force_rollback=True):
        run_month(conn, "2024-08", "basis", () if approved else ("R-DQ05",), write_files=False)
        result = calibrate(conn)
    # Tab1–Tab12 must match exactly; the reworked R-DQ05 (day/month swap) only changes single ages (Tab13), totals stay equal
    assert result["cells"] == 2880
    assert [m for m in result["mismatches"] if m[0] != "Tab13"] == []
    assert all(m[4].startswith("Alter ") and not m[4].startswith("Alter Insgesamt") for m in result["mismatches"])
    # SW-10: read like the example report (age = year − birth year for month 13) every one of the 2,880 cells matches
    if result["mismatches"]:
        assert result["explained"] and result["example_reading"]["mismatches"] == 0


def test_sheet_totals_equal_stat(conn, tmp_path, monkeypatch):
    from statagent.reporting import sheet
    monkeypatch.setattr(sheet, "OUT_DIR", tmp_path)
    with conn.transaction(force_rollback=True):
        r = sheet.build_sheet(conn, "basis")
    assert r["checked"] == 96


def test_approvals_need_a_named_person(conn):
    from statagent.core import rules
    for name in ("Team", "agent", "", "KI", "StatAgent-Agent", "Probe Tester", "Demo-Person"):
        with pytest.raises(ValueError):
            rules.decide(conn, "R-DQ03", name, True)


def test_generated_code_refuses_to_run_without_approval(conn):
    from statagent.agents import codegen
    from statagent.config import BASE_DIR
    with conn.transaction(force_rollback=True):
        c = codegen.propose(conn, "Test", {"group_by": ["geschlecht"], "months": ["2026-07"], "rule_set": "basis", "label": "Test"})
        try:
            with pytest.raises(PermissionError, match="freigegeben"):
                codegen.guard(conn, c["proposal_id"])          # proposed, not approved
            codegen.decide(conn, c["proposal_id"], "Erika Mustermann", True)
            assert codegen.guard(conn, c["proposal_id"])[1] == c["sha256"]
            (BASE_DIR / c["path"]).write_text(c["content"] + "\n# verändert\n", encoding="utf-8")
            with pytest.raises(PermissionError, match="verändert"):
                codegen.guard(conn, c["proposal_id"])          # approved, but the file changed afterwards
        finally:
            (BASE_DIR / c["path"]).unlink(missing_ok=True)


def test_read_only_connection_rejects_writes():
    from statagent.config import connect_readonly
    with connect_readonly() as ro:
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            ro.execute("UPDATE ops.rule SET title = title WHERE false")


def test_change_orders_1_and_2_end_to_end_rolled_back(conn):
    """Orders 1 + 2 as the agent proposes them, approved only inside this rolled-back transaction (never committed)."""
    from statagent.agents.coordinator import ORDER_RULES
    from statagent.config import setup_logging
    from statagent.etl import classification
    from statagent.qa.run import run_month
    import json
    with conn.transaction(force_rollback=True):
        for key, params in (("order1", {"version": "Beschaeftigungskategorie", "valid_from": "2024-08-01"}), ("order2", {})):
            spec = ORDER_RULES[key]
            conn.execute("""INSERT INTO ops.rule (rule_id, problem_id, type, title, description, action, parameters, rule_set, created_by,
                              status, approved_by, approved_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, 'auftraege', 'Test', 'approved', 'Probe Tester', now())
                            ON CONFLICT (rule_id) DO UPDATE SET status = 'approved', approved_by = 'Probe Tester'""",
                         (spec["rule_id"], spec["problem_id"], spec["type"], spec["title"], spec["description"], spec["action"], json.dumps(params)))
        classification.build(conn, setup_logging("test"))
        levels = conn.execute("SELECT code FROM klass_qualifikation WHERE version = 'Beschaeftigungskategorie' ORDER BY code").fetchall()
        assert [r[0] for r in levels] == ["Angestellte", "Arbeiter", "Beamte", "UNB"]
        r = run_month(conn, "2026-07", "auftraege", write_files=False)
        cats = dict(conn.execute("""SELECT qualifikation, sum(wert) FROM stat_beschaeftigte WHERE regelwerk = 'auftraege'
                                    AND stand = 'Lieferung 2026-07' GROUP BY 1""").fetchall())
        assert set(cats) <= {"Arbeiter", "Angestellte", "Beamte", "UNB"}
        assert r["metrics"]["records_total"] >= 399_027          # whole month ≥ Stichtag
        kind = conn.execute("SELECT DISTINCT zeitraum_art FROM stat_beschaeftigte WHERE regelwerk = 'auftraege'").fetchall()
        assert kind == [("Monat",)]


def test_published_month_is_frozen(conn):
    """Z4: after publication a run with different rules must not overwrite the month (rolled back)."""
    from statagent.qa.run import RunError, run_month
    if conn.execute("SELECT status FROM ops.rule WHERE rule_id = 'R-DQ05'").fetchone()[0] != "proposed":
        pytest.skip("R-DQ05 ist bereits entschieden – kein Regelunterschied zum Testen")
    with conn.transaction(force_rollback=True):
        conn.execute("UPDATE stat_beschaeftigte SET status = 'endgueltig' WHERE regelwerk = 'basis' AND stand = 'Lieferung 2024-08'")
        conn.execute("UPDATE ops.rule SET status = 'approved', approved_by = 'Probe Tester' WHERE rule_id = 'R-DQ05' AND status = 'proposed'")
        with pytest.raises(RunError, match="veröffentlicht"):
            with conn.transaction():
                run_month(conn, "2024-08", "basis", write_files=False)


def test_dynamic_handling_works_on_a_copy_only(conn):
    """Chat option 'exclude DQ-05' changes only the answer (copy in work.dq_copy), never store/stat (rolled back)."""
    from statagent.reporting import quality, tools
    before = conn.execute("SELECT sum(wert) FROM stat_beschaeftigte WHERE regelwerk = 'basis' AND stand = 'Lieferung 2024-08'").fetchone()[0]
    with conn.transaction(force_rollback=True):
        res = tools.query_stat(conn, "basis", ["2024-08"], ["alter"], {}, "bestand")
        issues = quality.detect(conn, "basis", ["2024-08"], ["alter"], {}, "bestand")
        dq05 = next(i for i in issues if i["problem_id"] == "DQ-05")
        assert dq05["affected"] == 370 and len(dq05["options"]) == 3
        h = quality.apply(conn, "Atest", "basis", ["2024-08"], {}, {"DQ-05": "ausschliessen"}, {}, "Probe Tester", issues)
        adj = quality.adjust(conn, res, h)
        assert sum(r["wert"] for r in adj["rows"]) == before - 370
        assert sum(r["offiziell"] for r in adj["rows"]) == before
        h2 = quality.apply(conn, "Atest2", "basis", ["2024-08"], {}, {}, {"DQ-05": "bitte ausschließen"}, "Probe Tester", issues)
        assert h2["applied"][0]["option_id"] == "ausschliessen"          # free text mapped to an option
    assert conn.execute("SELECT sum(wert) FROM stat_beschaeftigte WHERE regelwerk = 'basis' AND stand = 'Lieferung 2024-08'").fetchone()[0] == before


def test_ambiguous_terms_ask_back(conn):
    from statagent.agents import chat, intent
    months = [r[0] for r in conn.execute("SELECT DISTINCT substr(stand, 11) FROM stat_beschaeftigte WHERE regelwerk = 'basis' ORDER BY 1")]
    for question, term in (("Wie viele Menschen arbeiten in Wien?", "personen"), ("Fluktuation je Wirtschaftszweig 2025", "fluktuation"),
                           ("Wie viele Arbeiter gab es im Juli 2026?", "kategorie"), ("Beschäftigte in Tirol 2025", "jahr"),
                           ("Beschäftigte nach Branche von 08/2024 bis 07/2026", "oenace_bruch")):
        p = intent.parse(question, months)
        clar = chat.next_ambiguity(conn, conn, question, p, {}, months)
        assert clar and clar["term"] == term, (question, clar)
    p = intent.parse("Fluktuationsrate je Wirtschaftszweig 2025", months)
    assert chat.next_ambiguity(conn, conn, "Fluktuationsrate je Wirtschaftszweig 2025", p, {}, months) is None


def test_rdq05_swap_and_exclusion_keep_reconciliation(conn):
    """Reworked R-DQ05 (preview): totals unchanged with the swap; with exclude = true 370 records are excluded but accounted for."""
    import json
    from statagent.qa.run import run_month
    with conn.transaction(force_rollback=True):
        r = run_month(conn, "2024-08", "basis", ("R-DQ05",), write_files=False)
        assert r["metrics"]["records_total"] == 392_236 and r["metrics"]["records_excluded_rule"] == 0
        conn.execute("UPDATE ops.rule SET parameters = %s WHERE rule_id = 'R-DQ05'", (json.dumps({"fallback": "unbekannt", "exclude": True}),))
        r = run_month(conn, "2024-08", "basis", ("R-DQ05",), write_files=False)
        assert r["metrics"]["records_total"] == 392_236 - 370 and r["metrics"]["records_excluded_rule"] == 370


def test_recount_on_the_copy_equals_official_without_changes(conn):
    """SW-07: Personen and Zu-/Abgänge recounted on the (empty) copy reproduce the official values exactly."""
    from statagent.reporting import quality, tools
    for measure, months, dims in (("personen", ["2026-07"], ["geschlecht"]), ("zugaenge", ["2025-03"], ["region"]),
                                  ("fluktuationsrate", ["2025-11"], [])):
        res = tools.query_stat(conn, "basis", months, dims, {}, measure)
        out = quality.recompute(conn, res, {"copy_id": "test-empty", "hidden_months": [], "sql": ""})
        assert len(out["rows"]) == len(res["rows"])
        assert all(r["wert"] == r["offiziell"] for r in out["rows"]), measure


def test_carry_forward_removes_the_fake_flows_of_the_incomplete_delivery(conn):
    """SW-07: with DQ-02 carried forward on a copy, the Abgänge 10/2025 drop far below the delivered value; published values stay."""
    from statagent.reporting import quality, tools
    res = tools.query_stat(conn, "basis", ["2025-10"], [], {}, "abgaenge")
    issues = quality.detect(conn, "basis", ["2025-10"], [], {}, "abgaenge")
    with conn.transaction(force_rollback=True):
        applied = quality.apply(conn, "test-dq02", "basis", quality.copy_months("abgaenge", ["2025-10"]), {}, {"DQ-02": "fortschreiben"},
                                {}, "Test", issues)
        out = quality.recompute(conn, res, applied)
    assert out["rows"][0]["offiziell"] == res["rows"][0]["wert"]
    assert out["rows"][0]["wert"] < res["rows"][0]["wert"] / 3
