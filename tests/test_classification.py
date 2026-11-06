"""Unit tests for the pure helpers of the classification builder (no database needed)."""
import datetime as dt

from statagent.etl.classification import ancestor, build_states, classify_relations, parents, parse_date, relation_type


def test_relation_type():
    assert relation_type(1, 1) == "1:1"
    assert relation_type(3, 1) == "1:n"
    assert relation_type(1, 2) == "n:1"
    assert relation_type(2, 2) == "m:n"


def test_classify_relations_merge_split_and_reorganisation():
    types = classify_relations([("a", "x"), ("b", "x"), ("c", "y"), ("c", "z"), ("d", "w"), ("e", "u"), ("e", "v"), ("f", "v")])
    assert types[("a", "x")] == types[("b", "x")] == "n:1"
    assert types[("c", "y")] == types[("c", "z")] == "1:n"
    assert types[("d", "w")] == "1:1"
    assert (types[("e", "u")], types[("e", "v")], types[("f", "v")]) == ("1:n", "m:n", "n:1")


def test_parse_date_both_formats_of_the_change_list():
    assert parse_date("2017-01-01T00:00:00") == dt.date(2017, 1, 1)
    assert parse_date("01.08.2023") == dt.date(2023, 8, 1)
    assert parse_date("Stand") is None
    assert parse_date("") is None


def test_parents_and_ancestor_from_file_order():
    entries = [(1, "A"), (2, "A01"), (3, "A011"), (2, "A02"), (1, "B"), (2, "B05")]
    parent = parents(entries)
    assert parent == {"A": None, "A01": "A", "A011": "A01", "A02": "A", "B": None, "B05": "B"}
    levels = {code: level for level, code in entries}
    assert ancestor(parent, levels, "A011", 1) == "A"
    assert ancestor(parent, levels, "A011", 2) == "A01"
    assert ancestor(parent, levels, "B", 2) is None


def test_build_states_uses_in_force_date_and_closes_vanished_codes():
    s1, s2, s3 = dt.date(2024, 1, 1), dt.date(2025, 1, 1), dt.date(2026, 1, 1)
    snapshots = {s1: {"1": ("Lenzing", "417"), "2": ("Alt", "417")},
                 s2: {"1": ("Lenzing an der Ager", "417")},
                 s3: {"1": ("Lenzing an der Ager", "417"), "3": ("Neu", "417")}}
    states = build_states(snapshots, {"1": {dt.date(2024, 11, 28)}})
    assert [(s["code"], s["value"][0], s["snapshot"], s["from"], s["to"]) for s in states] == [
        ("1", "Lenzing", s1, s1, dt.date(2024, 11, 27)),
        ("1", "Lenzing an der Ager", s2, dt.date(2024, 11, 28), None),
        ("2", "Alt", s1, s1, dt.date(2024, 12, 31)),
        ("3", "Neu", s3, s3, None),
    ]
