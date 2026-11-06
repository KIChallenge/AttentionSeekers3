"""Unit tests without a database: claim check, German intent parser, generated-code SQL, ministry day plan."""
import pytest

from statagent.agents import codegen, intent
from statagent.reporting import claims, ministry

MONTHS = [f"{y}-{m:02d}" for y, m in [(2024, 8), (2024, 9), (2024, 10), (2024, 11), (2024, 12)] + [(2025, m) for m in range(1, 13)]
          + [(2026, m) for m in range(1, 8)]]


# --- claim check -------------------------------------------------------------------------------

def test_claim_check_accepts_numbers_from_the_result():
    r = claims.check("Juli 2026: Männer 213.129 (53,4 %), Frauen 185.898. Insgesamt 399.027.", [213129, 185898, 399027, 53.4],
                     {"months": ["2026-07"]})
    assert r["passed"] and r["numbers_checked"] == 4


def test_claim_check_rejects_an_invented_number():
    r = claims.check("Im Juli 2026 waren es 400.000 Verhältnisse.", [399027], {"months": ["2026-07"]})
    assert not r["passed"] and r["failed"] == 1


def test_claim_check_ignores_dates_ids_and_labels():
    text = "Stichtag 31.07.2026, Lauf 42, Regel R-DQ01 (DQ-01), ÖNACE 2025, Altersgruppe 15–19: 3.000."
    r = claims.check(text, [3000], {"months": ["2026-07"], "labels": ["15–19"]})
    assert r["passed"]


# --- intent parser -----------------------------------------------------------------------------

def test_parse_men_and_women_july_2026():
    p = intent.parse("Wie viele Männer und Frauen waren im Juli 2026 beschäftigt?", MONTHS)
    assert p["kind"] == "stat" and p["months"] == ["2026-07"] and p["dimensions"] == ["geschlecht"] and p["measure"] == "bestand"


def test_parse_time_series_range():
    p = intent.parse("Zeitreihe der Beschäftigten 08/2024 bis 07/2026", MONTHS)
    assert p["months"] == MONTHS and p["dimensions"] == []


def test_fluktuation_is_ambiguous_but_rate_is_not():
    assert intent.parse("Fluktuation je Wirtschaftszweig 2025", MONTHS)["ambiguous"] == ["fluktuation"]
    p = intent.parse("Fluktuationsrate je Wirtschaftszweig 2025", MONTHS)
    assert p["ambiguous"] == [] and p["measure"] == "fluktuationsrate" and p["dimensions"] == ["oenace"]
    assert p["months"] == [m for m in MONTHS if m.startswith("2025")]


def test_parse_metadata_questions():
    assert intent.parse("Was ist aus ÖNACE-Abschnitt J geworden?", MONTHS)[ "kind"] == "explain"
    p = intent.parse("Erkläre Gemeinde 62388", MONTHS)
    assert (p["kind"], p["klass"], p["code"]) == ("explain", "region", "62388")
    assert intent.parse("Welche Annahmen gelten für Lieferung 2025-10?", MONTHS)["months"] == ["2025-10"]


def test_follow_up_keeps_the_previous_period():
    first = intent.parse("Wie viele Männer und Frauen waren im Juli 2026 beschäftigt?", MONTHS)
    follow = intent.merge_follow_up(intent.parse("und nach Bundesland?", MONTHS), first, "und nach Bundesland?")
    assert follow["months"] == ["2026-07"] and follow["dimensions"] == ["geschlecht", "region"]


def test_instructions_are_routed_to_the_roles():
    assert intent.parse_instruction("Setze Änderungsauftrag 1 um", MONTHS)["role"] == "Klassifikation"
    assert intent.parse_instruction("Ganzes Monat statt Stichtag zählen", MONTHS)["intent"] == "order2"
    o3 = intent.parse_instruction("Lieferung an das Ministerium für 07/2026", MONTHS)
    assert o3["intent"] == "order3" and o3["params"]["report_month"] == "2026-07" and o3["params"]["min_days"] == 200
    sp = intent.parse_instruction("Beschäftigte in 5-Jahres-Altersgruppen, Wien gesondert, ohne Beamte", MONTHS)
    assert sp["intent"] == "special" and "altersgruppe5" in sp["params"]["group_by"] and "wien_rest" in sp["params"]["group_by"]
    assert sp["params"]["exclude"] == {"qualifikation": ["Beamte"]}


def test_live_change_variants():
    a = intent.parse_instruction("Beschäftigte nach Altersgruppen 15-24, 25-49 und 50 und älter für Juli 2026", MONTHS)
    assert a["params"]["group_by"] == ["altersbaender"] and a["params"]["age_bounds"] == [15, 25, 50]
    assert "'25–49'" in codegen.build_sql(a["params"])
    b = intent.parse_instruction("Nur Frauen, nach Arbeiter, Angestellte und Beamte, Juli 2026", MONTHS)
    assert b["intent"] == "special" and b["params"]["group_by"] == ["kategorie"] and b["params"]["filters"] == {"geschlecht": ["W"]}
    c = intent.parse_instruction("Zeig die Beschäftigten in 5-Jahres-Altersgruppen, nur Tirol", MONTHS)
    assert c["params"]["filters"] == {"region": ["7"]}


# --- generated code ----------------------------------------------------------------------------

def test_generated_sql_is_literal_and_validated():
    sql = codegen.build_sql({"group_by": ["altersgruppe5", "wien_rest"], "months": ["2026-07"], "exclude": {"qualifikation": ["Beamte"]},
                             "rule_set": "basis"})
    assert "qualifikation NOT IN ('Beamte')" in sql and "'Lieferung 2026-07'" in sql
    with pytest.raises(ValueError):
        codegen.build_sql({"group_by": ["region"], "months": ["2026-07'; DROP TABLE x; --"]})
    with pytest.raises(ValueError):
        codegen.build_sql({"group_by": ["unbekannt"], "months": ["2026-07"]})
    with pytest.raises(ValueError):
        codegen.build_sql({"group_by": ["region"], "months": ["2026-07"], "exclude": {"1=1) OR (true": ["x"]}})


# --- ministry delivery --------------------------------------------------------------------------

def test_ministry_uses_the_latest_delivery_per_day_but_never_a_later_one():
    plan = ministry.plan("2026-07", 12, MONTHS)
    assert [d["month"] for d in plan][0] == "2025-08" and plan[-1]["month"] == "2026-07"
    source = {d["month"]: d["delivery"] for d in plan}
    assert source["2025-08"] == "2025-10"           # the incomplete delivery (DQ-02) → handled by the rule parameter
    assert source["2026-05"] == "2026-07" and source["2026-07"] == "2026-07"


def test_birth_year_rules():
    import datetime as dt
    ref = dt.date(2026, 7, 31)
    assert ministry.birth_year("1987-13-05", ref, 110) == "1987"       # DQ-05: year plausible
    assert ministry.birth_year("1850-12-14", ref, 110) == "Unbekannt"  # DQ-06
    assert ministry.birth_year(None, ref, 110) == "Unbekannt"
