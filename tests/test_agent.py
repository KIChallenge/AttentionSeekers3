"""Unit tests without a database for the data agent: scope gate, English/pension parsing, chart choice, model tool calls
(the model is replaced by a fake – no key, no network)."""
from statagent.agents import chat, intent, llm

MONTHS = [f"{y}-{m:02d}" for y, m in [(2024, 8), (2024, 9), (2024, 10), (2024, 11), (2024, 12)] + [(2025, m) for m in range(1, 13)]
          + [(2026, m) for m in range(1, 8)]]


def test_questions_outside_the_data_are_declined():
    for q in ("Wer war Napoleon?", "Was ist die Lichtgeschwindigkeit?", "Wann war der Wiener Kongress 1815?",
              "Wie viele Planeten hat das Sonnensystem?", "Hallo"):
        assert intent.parse(q, MONTHS)["kind"] == "out_of_scope", q


def test_questions_about_the_data_are_not_declined():
    assert intent.parse("Wie viele in Tirol?", MONTHS)["kind"] == "stat"
    assert intent.parse("Zeitreihe der Beschäftigten", MONTHS)["kind"] == "stat"
    assert intent.parse("Wie hoch ist das Einkommen in Wien?", MONTHS)["kind"] == "unavailable"


def test_english_men_and_women_june_2026():
    p = intent.parse("Show me all men and women that worked in 2026 in june", MONTHS)
    assert p["kind"] == "stat" and p["months"] == ["2026-06"] and p["dimensions"] == ["geschlecht"]


def test_pension_questions_go_to_the_pension_statistic():
    p = intent.parse("Pensionen 2023 nach Geschlecht", MONTHS)
    assert p["kind"] == "pension" and p["years"] == [2023] and p["dimensions"] == ["geschlecht"]
    p = intent.parse("Entwicklung der Korridorpensionen", MONTHS)
    assert p["years"] == list(range(2018, 2026)) and p["filters"] == {"pensionsart": ["KOR"]}


def test_chart_wish_only_where_the_data_fit():
    card = {"unit": "Anzahl", "chart": {"kind": "bar", "x": "geschlecht_label", "series": [{"key": "wert"}],
                                        "data": [{"geschlecht_label": "Männer", "wert": 1}, {"geschlecht_label": "Frauen", "wert": 2}]}}
    chat.apply_chart(card, "donut")
    assert card["chart"]["kind"] == "donut"
    chat.apply_chart(card, "line")                      # no time axis → stays
    assert card["chart"]["kind"] == "donut"
    chat.apply_chart(card, "none")
    assert card["chart"] is None


def _fake_model(monkeypatch, name, arguments):
    monkeypatch.setattr(chat, "llm_status", lambda: {"configured": True, "mode_label": "Agent · Test"})
    monkeypatch.setattr(llm, "chat", lambda *a, **k: {"tool_calls": [{"id": "1", "name": name, "arguments": arguments}],
                                                      "content": "", "model": "fake-model"})


def test_agent_tool_call_becomes_validated_parameters(monkeypatch):
    _fake_model(monkeypatch, "query_employment", {"measure": "bestand", "months": ["2026-06"], "dimensions": ["geschlecht"], "chart": "donut"})
    p = chat.llm_parse("Show me all men and women that worked in 2026 in june", MONTHS, None)
    assert p["kind"] == "stat" and p["months"] == ["2026-06"] and p["dimensions"] == ["geschlecht"]
    assert p["chart_pref"] == "donut" and p["agent_tool"] == "query_employment" and p["model"] == "fake-model"


def test_agent_can_decline(monkeypatch):
    _fake_model(monkeypatch, "decline_out_of_scope", {"topic": "Geschichte"})
    p = chat.llm_parse("Wer war Napoleon?", MONTHS, None)
    assert p["kind"] == "out_of_scope" and p["topic"] == "Geschichte"


def test_deterministic_missing_fields_win_over_the_model(monkeypatch):
    _fake_model(monkeypatch, "query_employment", {"measure": "bestand", "filters": {"region": ["9"]}})
    assert chat.llm_parse("Wie hoch ist das Einkommen in Wien?", MONTHS, None)["kind"] == "unavailable"


def test_model_answering_off_topic_without_parameters_is_still_declined(monkeypatch):
    _fake_model(monkeypatch, "query_employment", {"measure": "bestand"})
    assert chat.llm_parse("Was ist die Lichtgeschwindigkeit?", MONTHS, None)["kind"] == "out_of_scope"


def test_provider_is_detected_from_the_key(monkeypatch):
    for k in ("AGENT_PROVIDER", "AGENT_MODEL", "AGENT_BASE_URL", "AZURE_OPENAI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("AGENT_API_KEY", "sk-ant-test")
    c = llm.llm_config()
    assert c["provider"] == "anthropic" and c["model"] and c["base_url"].startswith("https://api.anthropic.com")
    monkeypatch.setenv("AGENT_API_KEY", "sk-test")
    assert llm.llm_config()["provider"] == "openai" and not llm.llm_status()["configured"]     # model name still missing
    monkeypatch.setenv("AGENT_MODEL", "some-model")
    assert llm.llm_status()["configured"]
