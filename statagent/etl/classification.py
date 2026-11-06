"""Classifications (Phase 2): klass_ tables, Übergänge and Quellzuordnung, built from the package files.

The files stay unchanged; everything is read from the raw tables filled by ``load``:

| Target              | Source                                                                                   |
| ------------------- | ---------------------------------------------------------------------------------------- |
| klass_geschlecht    | geschlecht.csv + UNB (DQ-15)                                                             |
| klass_qualifikation | qualifikation.csv (Beschäftigungskategorie and FD flag as attributes) + UNB (DQ-15)      |
| klass_alter         | completed years 0–110, report groups "bis 14" / "75 u. mehr" (example report Tab13), UNB |
| klass_region        | regionen/bundeslaender.csv + bundesland.csv (code 0, KL-01), bezirke_/gemeinden_JJJJ-01-01 |
| klass_oenace        | oenace/OENACE2003_DE_COT, OENACE2008/2025_DE_CTI + _COT, oenace_2008/2025.csv (labels, UNB) |
| klass_uebergang     | OENACE…_12B.txt (Unterklassen) + derived sections; regionen ODS change lists + snapshot diffs |
| quellzuordnung      | how the deliveries write each attribute (quelle 'ZVD-Monatslieferung')                   |

- The Anhang-B tables keep their prescribed German column names and attribute keys; this code is English.
- Columns of the source files are found by their header, never by position.
- Regions are historised as states: a new state starts when the name or the parent changes. Its version
  is 'Stand JJJJ-01-01' (first snapshot showing it). The boundary between two snapshots is the in-force
  date from the change lists if there is one, else the later snapshot date.
- Mappings that rest on an assumption are generated from the parameters of their rule (action
  'source_mapping', e.g. R-DQ07, R-DQ08) and take effect only once the rule is approved
  (view quellzuordnung_wirksam).
- All tables are rebuilt in one transaction; every build is a run in ops.run with a checksum (T1).
- ``check_mappings`` checks every value in the deliveries: it must lead to exactly one valid code.
- Report texts are German (shown to users); findings carry their Problems.md IDs.
"""
import datetime as dt
import hashlib
import json
import re
from collections import Counter, defaultdict

from statagent.config import connect, setup_logging
from statagent.core.labels import RULE_STATUS, label

SOURCE = "ZVD-Monatslieferung"           # quellzuordnung.quelle of the monthly deliveries
KLASS_TABLES = ("klass_geschlecht", "klass_qualifikation", "klass_alter", "klass_region", "klass_oenace")
KLASS_COLUMNS = ("version", "code", "bezeichnung", "ebene", "uebergeordnet", "gueltig_von", "gueltig_bis", "attribute")
TRANSITION_COLUMNS = ("klassifikation", "version_alt", "code_alt", "version_neu", "code_neu", "beziehung", "gueltig_ab",
                      "quelle", "anmerkung", "anteil")
MAPPING_COLUMNS = ("quelle", "merkmal", "quellwert", "klassifikation", "version", "code", "gueltig_von",
                   "gueltig_bis", "regel_id")
DQ15 = "StatAgent (DQ-15: Klassifikationsdatei ohne Ausprägung unbekannt)"
MAX_AGE = 110            # older ages are implausible (DQ-06) and belong to UNB; example report: 7 cases in 08/2024
EPOCH = dt.date(1, 1, 1)
DAY = dt.timedelta(days=1)

OENACE_DIR = "klassifikationen/oenace/"
OENACE_LEVELS = ("Abschnitt", "Abteilung", "Gruppe", "Klasse", "Unterklasse")
OENACE = {  # version: (valid from, valid to, file with the titles, file with the explanations, levels)
    "2003": (dt.date(2003, 1, 1), dt.date(2007, 12, 31), "OENACE2003_DE_COT.txt", "OENACE2003_DE_COT.txt",
             ("Abschnitt", "Unterabschnitt", "Abteilung", "Gruppe", "Klasse", "Unterklasse")),
    "2008": (dt.date(2008, 1, 1), dt.date(2024, 12, 31), "OENACE2008_DE_CTI.txt", "OENACE2008_DE_COT.txt", OENACE_LEVELS),
    "2025": (dt.date(2025, 1, 1), None, "OENACE2025_DE_CTI.txt", "OENACE2025_DE_COT.txt", OENACE_LEVELS),
}
CORRESPONDENCES = (("2003", "2008", "OENACE2003_OENACE2008_DE_12B.txt"), ("2008", "2025", "OENACE2008_OENACE2025_DE_12B.txt"))

REGION_FILE = re.compile(r"^klassifikationen/regionen/(gemeinden|bezirke)_(\d{4}-\d{2}-\d{2})\.csv$")
BUNDESLAENDER_FILE = "klassifikationen/regionen/bundeslaender.csv"
ODS_FILE = "aenderungenGemeinden_ab2002.ods"      # found by name: its folder name is damaged (ENV-03)
ODS_TRANSITION_SHEETS = {  # sheet: type of change (None = column 'Änderungsgrund')
    "alle_GKZaenderungen": None,
    "Zusammenlegungen": "Zusammenlegung",
    "Teilungen": "Teilung",
    "Bezirkszusammenlegungen": "Bezirkszusammenlegung",
}

# Delivery field -> (classification, periods by reporting month: (version, valid from, valid to, basic table)).
# Version None = version of the Bundesland states (first region snapshot).
FIELDS = {
    "GESCHLECHT": ("klass_geschlecht", [("-", EPOCH, None, "geschlecht")]),
    "QUAL": ("klass_qualifikation", [("-", EPOCH, None, "qualifikation")]),
    "BUNDESLAND": ("klass_region", [(None, EPOCH, None, "bundesland")]),
    "OENACE": ("klass_oenace", [("2008", OENACE["2008"][0], OENACE["2008"][1], "oenace_2008"),
                                ("2025", OENACE["2025"][0], OENACE["2025"][1], "oenace_2025")]),
}


# --- pure helpers ----------------------------------------------------------------------------

def parse_date(text: str | None) -> dt.date | None:
    """ISO date (also with time, as stored for spreadsheet dates) or TT.MM.JJJJ (both occur in the ODS)."""
    if not text:
        return None
    if m := re.match(r"^(\d{4})-(\d{2})-(\d{2})", text):
        return dt.date(*map(int, m.groups()))
    if m := re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", text):
        day, month, year = map(int, m.groups())
        return dt.date(year, month, day)
    return None


def relation_type(n_targets: int, n_sources: int) -> str:
    """Relation type of a pair from the old code's number of targets and the new code's number of sources."""
    if n_targets == 1:
        return "1:1" if n_sources == 1 else "n:1"
    return "1:n" if n_sources == 1 else "m:n"


def classify_relations(pairs) -> dict:
    """Relation type per (old, new) pair within one set of pairs."""
    pairs = list(dict.fromkeys(pairs))
    targets, sources = Counter(a for a, _ in pairs), Counter(n for _, n in pairs)
    return {(a, n): relation_type(targets[a], sources[n]) for a, n in pairs}


def parents(entries) -> dict[str, str | None]:
    """Parent code per (level, code) entry from the hierarchical file order: nearest preceding entry one level up."""
    last, result = {}, {}
    for level, code in entries:
        result[code] = last.get(level - 1) if level > 1 else None
        last[level] = code
    return result


def ancestor(parent: dict, levels: dict, code: str, level: int) -> str | None:
    while code is not None and levels.get(code, 0) > level:
        code = parent.get(code)
    return code if code is not None and levels.get(code) == level else None


def build_states(snapshots: dict, events: dict) -> list[dict]:
    """Historised states from snapshots {date: {code: value}} with value = (name, parent).

    A state ends when the code disappears or its value changes. The boundary between two snapshots is the
    latest event date of the code in between (in-force date from the change lists), else the later snapshot.
    """
    days = sorted(snapshots)
    result = []
    for code in sorted(set().union(*snapshots.values())):
        current = None
        for i, day in enumerate(days):
            value = snapshots[day].get(code)
            if (current and value == current["value"]) or (current is None and value is None):
                continue
            boundary = day if i == 0 else max((e for e in events.get(code, ()) if days[i - 1] < e <= day), default=day)
            if current:
                result.append({**current, "to": boundary - DAY})
            current = {"code": code, "value": value, "snapshot": day, "from": boundary, "to": None} if value else None
        if current:
            result.append(current)
    return result


def state_at(by_code: dict, code: str, day: dt.date) -> dict | None:
    return next((s for s in by_code.get(code, ()) if s["from"] <= day and (s["to"] is None or day <= s["to"])), None)


def klass_row(version, code, label_, level, parent=None, valid_from=None, valid_to=None, **attribute) -> dict:
    return {"version": version, "code": code, "bezeichnung": label_, "ebene": level, "uebergeordnet": parent,
            "gueltig_von": valid_from, "gueltig_bis": valid_to, "attribute": attribute}


def transition_row(klassifikation, version_old, code_old, version_new, code_new, relation, valid_from, source,
                   note=None, share=None) -> dict:
    return dict(zip(TRANSITION_COLUMNS, (klassifikation, version_old, code_old, version_new, code_new, relation,
                                         valid_from, source, note, share)))


def _examples(values, n: int = 5) -> str:
    values = list(values)
    return ", ".join(map(str, values[:n])) + (f" … (+{len(values) - n})" if len(values) > n else "")


# --- reading the raw tables ------------------------------------------------------------------

def read_text_file(conn, rel: str) -> list[dict]:
    """Rows of a delimited package file as dicts keyed by the header; '_line' = line number."""
    rows = conn.execute("SELECT line_no, fields FROM roh.text_line WHERE path = %s ORDER BY line_no", (rel,)).fetchall()
    if not rows:
        raise RuntimeError(f"{rel} ist nicht geladen – zuerst `python -m statagent laden` ausführen")
    header = [h.strip() for h in rows[0][1]]
    return [{**dict(zip(header, (f.strip() for f in fields))), "_line": line_no} for line_no, fields in rows[1:]]


def read_sheet(conn, rel: str, sheet: str) -> list[dict]:
    """Rows of a spreadsheet sheet as dicts keyed by its header row (first row with at least 5 cells)."""
    cells = defaultdict(dict)
    for row_no, col_no, value in conn.execute("SELECT row_no, col_no, value FROM roh.cell WHERE path = %s AND sheet = %s",
                                              (rel, sheet)):
        cells[row_no][col_no] = value.strip()
    header_row = next((r for r in sorted(cells) if len(cells[r]) >= 5), None)
    if header_row is None:
        raise RuntimeError(f"{rel}: Blatt {sheet} fehlt oder hat keine Kopfzeile")
    names = cells[header_row]
    return [{**{names[c]: v for c, v in cells[r].items() if c in names}, "_line": r} for r in sorted(cells) if r > header_row]


def basic_classifications(conn) -> dict[str, list[tuple]]:
    """The five basic classification files as loaded unchanged into klassifikation.*."""
    return {t: conn.execute(f"SELECT * FROM klassifikation.{t} ORDER BY code").fetchall()
            for t in ("geschlecht", "qualifikation", "bundesland", "oenace_2008", "oenace_2025")}


# --- small classifications -------------------------------------------------------------------

def build_sex(basic) -> list[dict]:
    rows = [klass_row("-", c, b, "Geschlecht", quelle="klassifikationen/geschlecht.csv") for c, b in basic["geschlecht"]]
    return rows + [klass_row("-", "UNB", "Geschlecht unbekannt", "Geschlecht", unbekannt=True, quelle=DQ15)]


def build_qualification(basic) -> list[dict]:
    rows = [klass_row("-", c, b, "Qualifikation", beschaeftigungskategorie=k, freier_dienstvertrag=(fd == "J"),
                      quelle="klassifikationen/qualifikation.csv") for c, b, k, fd in basic["qualifikation"]]
    return rows + [klass_row("-", "UNB", "Qualifikation unbekannt", "Qualifikation", unbekannt=True, quelle=DQ15)]


def build_category_level(conn, basic) -> tuple[list[dict], list[dict], list[str]]:
    """Change order 1: level Beschäftigungskategorie (Arbeiter, Angestellte, Beamte) as its own version of
    klass_qualifikation – only once a rule with action 'category_level' is approved. Codes and labels come from the
    column BESCHAEFTIGUNGSKATEGORIE of qualifikation.csv (data, T3); its own version avoids a clash with the
    Qualifikation code 'Beamte' (key: version + code). Transitions Qualifikation -> category are n:1."""
    rules = conn.execute("""SELECT rule_id, parameters FROM ops.rule WHERE action = 'category_level' AND status = 'approved'
                            ORDER BY rule_id""").fetchall()
    if not rules:
        return [], [], []
    rule_id, params = rules[-1]
    version = (params or {}).get("version", "Beschaeftigungskategorie")
    valid_from = parse_date((params or {}).get("valid_from")) or dt.date(2024, 8, 1)
    categories = []
    for _, _, k, _ in basic["qualifikation"]:
        if k not in categories:
            categories.append(k)
    rows = [klass_row(version, k, k, "Beschäftigungskategorie", None, valid_from, quelle="klassifikationen/qualifikation.csv "
                      "(Spalte BESCHAEFTIGUNGSKATEGORIE)", regel=rule_id) for k in categories]
    rows.append(klass_row(version, "UNB", "Beschäftigungskategorie unbekannt", "Beschäftigungskategorie", None, valid_from,
                          unbekannt=True, quelle=DQ15, regel=rule_id))
    pairs = [(c, k) for c, _, k, _ in basic["qualifikation"]] + [("UNB", "UNB")]
    types = classify_relations(pairs)
    transitions = [transition_row("klass_qualifikation", "-", c, version, k, types[(c, k)], valid_from,
                                  "klassifikationen/qualifikation.csv", f"Änderungsauftrag 1, Regel {rule_id}: DV und FD zusammen")
                   for c, k in pairs]
    return rows, transitions, [rule_id]


def build_age() -> list[dict]:
    source = "Fachbeschreibung §4 Regel 5; Gruppen laut beispielbericht_2024-08.xlsx Tab13"
    rows = [klass_row("-", "bis14", "bis 14 Jahre", "Altersgruppe", berichtszeile="bis 14", quelle=source),
            klass_row("-", "75+", "75 Jahre und mehr", "Altersgruppe", berichtszeile="75 u. mehr", quelle=source)]
    for n in range(MAX_AGE + 1):
        group = "bis14" if n <= 14 else "75+" if n >= 75 else None
        rows.append(klass_row("-", str(n), "1 Jahr" if n == 1 else f"{n} Jahre", "Altersjahr", group,
                              berichtszeile={"bis14": "bis 14", "75+": "75 u. mehr"}.get(group, str(n)), quelle=source))
    return rows + [klass_row("-", "UNB", "Alter unbekannt", "Altersjahr", unbekannt=True, berichtszeile="unbekannt",
                             anmerkung=f"Alter nicht bestimmbar: Geburtsdatum fehlt oder ist nicht plausibel "
                                       f"(z. B. Alter über {MAX_AGE} Jahre, DQ-06)", quelle=source)]


# --- regions ---------------------------------------------------------------------------------

def build_region(conn, basic) -> tuple[list[dict], list[dict], list[str], dict]:
    """klass_region (Bundesland / Bezirk / Gemeinde states 2011–2026) and its transitions."""
    findings: list[str] = []
    municipalities, districts, municipality_rows = {}, {}, {}
    for (rel,) in conn.execute("SELECT path FROM roh.file WHERE path LIKE 'klassifikationen/regionen/%%' ORDER BY path").fetchall():
        if m := REGION_FILE.match(rel):
            day, rows = dt.date.fromisoformat(m.group(2)), read_text_file(conn, rel)
            if m.group(1) == "gemeinden":
                municipalities[day] = {r["GEMEINDE_CODE"]: (r["GEMEINDE"], r["BEZIRK_CODE"]) for r in rows}
                municipality_rows[day] = rows
            else:
                districts[day] = {r["BEZIRK_CODE"]: (r["BEZIRK"], r["BUNDESLAND_CODE"]) for r in rows}
    if not municipalities or set(municipalities) != set(districts):
        raise RuntimeError("Regionen: Gemeinde- und Bezirksstände fehlen oder passen nicht zusammen")
    first, last = min(municipalities), max(municipalities)

    # Consistency of the snapshot files (LIESMICH: Bezirk = first three digits, Bundesland = first digit).
    inconsistent = [f"{d} {r['GEMEINDE_CODE']}" for d, rows in municipality_rows.items() for r in rows
                    if r["BEZIRK_CODE"] != r["GEMEINDE_CODE"][:3] or r["BUNDESLAND_CODE"] != r["GEMEINDE_CODE"][:1]
                    or districts[d].get(r["BEZIRK_CODE"], ("",))[0] != r["BEZIRK"]]
    if inconsistent:
        findings.append(f"KL-03: {len(inconsistent)} Gemeindezeilen passen nicht zu Code-Aufbau oder Bezirksdatei: {_examples(inconsistent)}")

    # Bundesländer: one concept from both files (KL-01).
    states_bl = {r["BUNDESLAND_CODE"]: r["BUNDESLAND"] for r in read_text_file(conn, BUNDESLAENDER_FILE)}
    basic_bl = dict(basic["bundesland"])
    differing = [f"{c}: {states_bl[c]} / {basic_bl.get(c)}" for c in states_bl if basic_bl.get(c) != states_bl[c]]
    findings.append("KL-01: Bundesland in bundesland.csv (mit 0) und regionen/bundeslaender.csv (ohne 0) – zu einer "
                    "klass_region zusammengeführt; " + (f"abweichende Bezeichnungen: {', '.join(differing)}"
                                                        if differing else "Bezeichnungen 1–9 identisch"))
    version0 = f"Stand {first}"
    rows = [klass_row(version0, c, n, "Bundesland", None, first, None, ebene_nr=1,
                      quelle=f"{BUNDESLAENDER_FILE}, klassifikationen/bundesland.csv") for c, n in sorted(states_bl.items())]
    rows += [klass_row(version0, c, n, "Bundesland", None, first, None, ebene_nr=1, unbekannt=True,
                       quelle="klassifikationen/bundesland.csv") for c, n in basic_bl.items() if c not in states_bl]

    # Official change lists: Gemeinde transitions with in-force date, type and legal basis.
    ods = conn.execute("SELECT path FROM roh.file WHERE path LIKE %s", (f"%/{ODS_FILE}",)).fetchone()
    if ods is None:
        raise RuntimeError(f"{ODS_FILE} ist nicht geladen")
    events: dict[tuple, dict] = {}
    for sheet, kind in ODS_TRANSITION_SHEETS.items():
        for r in read_sheet(conn, ods[0], sheet):
            old, new, day = r.get("Gemeindekennziffer alt", ""), r.get("Gemeindekennziffer neu", ""), parse_date(r.get("in Kraft seit"))
            if old.isdigit() and new.isdigit() and day:
                e = events.setdefault((day, old, new), {"kinds": set(), "legal_bases": [], "sources": []})
                e["kinds"].add(kind or r.get("Änderungsgrund") or "Kennziffernänderung")
                if (g := r.get("Gesetzliche bzw. amtliche Grundlagen")) and g not in e["legal_bases"]:
                    e["legal_bases"].append(g)
                e["sources"].append(f"{ODS_FILE} {sheet} Z{r['_line']}")
    renames = [(parse_date(r.get("in Kraft seit")), r["Gemeindekennziffer"], r.get("Gemeindename alt", ""),
                r.get("Gemeindename neu", ""), r.get("Gesetzliche bzw. amtliche Grundlagen", ""), r["_line"])
               for r in read_sheet(conn, ods[0], "Namensaenderungen") if r.get("Gemeindekennziffer", "").isdigit()]

    municipality_events, district_events = defaultdict(set), defaultdict(set)
    for day, old, new in events:
        municipality_events[old].add(day)
        municipality_events[new].add(day)
        if old[:3] != new[:3]:
            district_events[old[:3]].add(day)
            district_events[new[:3]].add(day)
    for day, code, *_ in renames:
        if day:
            municipality_events[code].add(day)

    municipality_states = build_states(municipalities, municipality_events)
    district_states = build_states(districts, district_events)
    for level, level_no, file_stem, states in (("Bezirk", 2, "bezirke", district_states), ("Gemeinde", 3, "gemeinden", municipality_states)):
        rows += [klass_row(f"Stand {s['snapshot']}", s["code"], s["value"][0], level, s["value"][1], s["from"], s["to"],
                           ebene_nr=level_no, quelle=f"klassifikationen/regionen/{file_stem}_{s['snapshot']}.csv") for s in states]
    municipality_by_code, district_by_code = defaultdict(list), defaultdict(list)
    for s in municipality_states:
        municipality_by_code[s["code"]].append(s)
    for s in district_states:
        district_by_code[s["code"]].append(s)
    municipality_by_version = {(f"Stand {s['snapshot']}", s["code"]): s for s in municipality_states}

    # Gemeinde transitions from the change lists, plus state changes of the same code (name, Bezirk).
    pairs: dict[tuple, dict] = {}
    before_first, unresolved, deviating = 0, [], []
    for (day, old, new), e in sorted(events.items()):
        if day <= first:
            before_first += 1
            continue
        s_old, s_new = state_at(municipality_by_code, old, day - DAY), state_at(municipality_by_code, new, day)
        if not (s_old and s_new):   # in-force date does not match the snapshots: nearest state before / after
            s_old = s_old or next((s for s in reversed(municipality_by_code.get(old, [])) if s["to"] and s["to"] < day), None)
            s_new = s_new or next((s for s in municipality_by_code.get(new, []) if s["from"] > day), None)
            if not (s_old and s_new):
                unresolved.append(f"{old}→{new} ({day})")
                continue
            deviating.append(f"{old}→{new} in Kraft {day:%d.%m.%Y}, Stände: {old} bis {s_old['to']:%d.%m.%Y}, "
                             f"{new} ab {s_new['from']:%d.%m.%Y}")
            e["kinds"].add(f"Datum laut Änderungsliste weicht von den Ständen ab ({new} ab {s_new['from']:%d.%m.%Y})")
        # Relation types are computed per state boundary (not per in-force date, which may deviate, see above).
        p = pairs.setdefault((f"Stand {s_old['snapshot']}", old, f"Stand {s_new['snapshot']}", new),
                             {"from": day, "group": s_old["to"] + DAY if s_old["to"] and s_old["to"] < day else day,
                              "notes": [], "sources": []})
        p["notes"].append(" + ".join(sorted(e["kinds"])) + "".join(f"; {g}" for g in e["legal_bases"]))
        p["sources"] += e["sources"]
    renames_seen = set()
    for code, states in sorted(municipality_by_code.items()):
        for old, new in zip(states, states[1:]):
            if old["to"] is None or old["to"] + DAY != new["from"]:
                continue
            text = [f"Name: {old['value'][0]} → {new['value'][0]}"] if old["value"][0] != new["value"][0] else []
            if old["value"][1] != new["value"][1]:
                text.append(f"Bezirk: {old['value'][1]} → {new['value'][1]}")
            sources = [f"gemeinden_{new['snapshot']}.csv"]
            for day, c, _, _, legal_basis, line in renames:
                if c == code and day and old["snapshot"] < day <= new["snapshot"]:
                    text.append(f"Namensänderung in Kraft {day:%d.%m.%Y}" + (f"; {legal_basis}" if legal_basis else ""))
                    sources.append(f"{ODS_FILE} Namensaenderungen Z{line}")
                    renames_seen.add((c, day))
            p = pairs.setdefault((f"Stand {old['snapshot']}", code, f"Stand {new['snapshot']}", code),
                                 {"from": new["from"], "group": new["from"], "notes": [], "sources": []})
            p["notes"].append("; ".join(text))
            p["sources"] += sources
    invisible = [f"{c} {a} → {n} ({d:%d.%m.%Y})" for d, c, a, n, *_ in sorted(renames, key=lambda x: (x[1], x[0] or EPOCH))
                 if d and first < d <= last and (c, d) not in renames_seen]
    if invisible:
        findings.append(f"KL-03: {len(invisible)} Namensänderungen der Änderungsliste zwischen zwei Ständen ohne "
                        f"Niederschlag in den Ständen: {_examples(invisible)}")
    if deviating:
        findings.append(f"KL-03: {len(deviating)} Übergänge mit Datum, das nicht zu den Ständen passt (Übergang trotzdem "
                        f"übernommen): {'; '.join(deviating)}")

    # Bezirk transitions, derived from Gemeinden that change their Bezirk, plus state changes of the same code.
    district_pairs: dict[tuple, dict] = {}
    for (vo, co, vn, cn), p in pairs.items():
        d_old, d_new = municipality_by_version[(vo, co)]["value"][1], municipality_by_version[(vn, cn)]["value"][1]
        if d_old == d_new:
            continue
        sd_old, sd_new = state_at(district_by_code, d_old, p["from"] - DAY), state_at(district_by_code, d_new, p["from"])
        if not (sd_old and sd_new):
            unresolved.append(f"Bezirk {d_old}→{d_new} ({p['from']})")
            continue
        dp = district_pairs.setdefault((f"Stand {sd_old['snapshot']}", d_old, f"Stand {sd_new['snapshot']}", d_new),
                                       {"from": p["from"], "group": p["group"], "n": 0, "kinds": set()})
        dp["n"] += 1
        dp["kinds"].update(a.split(";")[0] for a in p["notes"])
    district_rows = {k: {"from": v["from"], "group": v["group"],
                         "notes": [f"abgeleitet aus {v['n']} Gemeinde-Übergang{'' if v['n'] == 1 else 'en'} "
                                   f"({', '.join(sorted(v['kinds']))})"],
                         "sources": [f"abgeleitet aus {ODS_FILE} und gemeinden_JJJJ-01-01.csv"]} for k, v in district_pairs.items()}
    for code, states in sorted(district_by_code.items()):
        for old, new in zip(states, states[1:]):
            if old["to"] is not None and old["to"] + DAY == new["from"]:
                text = [f"Name: {old['value'][0]} → {new['value'][0]}"] if old["value"][0] != new["value"][0] else []
                if old["value"][1] != new["value"][1]:
                    text.append(f"Bundesland: {old['value'][1]} → {new['value'][1]}")
                district_rows[(f"Stand {old['snapshot']}", code, f"Stand {new['snapshot']}", code)] = {
                    "from": new["from"], "group": new["from"], "notes": ["; ".join(text)],
                    "sources": [f"bezirke_{new['snapshot']}.csv"]}

    transitions = []
    for group in (pairs, district_rows):
        by_day = defaultdict(list)
        for k, p in group.items():
            by_day[p["group"]].append(((k[0], k[1]), (k[2], k[3])))
        types = {pair: t for pairs_ in by_day.values() for pair, t in classify_relations(pairs_).items()}
        transitions += [transition_row("klass_region", vo, co, vn, cn, types[((vo, co), (vn, cn))], p["from"],
                                       "; ".join(dict.fromkeys(p["sources"])), " | ".join(dict.fromkeys(p["notes"])))
                        for (vo, co, vn, cn), p in sorted(group.items())]

    # Cross-check (KL-03): every code that disappears or appears after the first snapshot needs a transition
    # from its last / to its first state.
    for level, by_code, group in (("Gemeinde", municipality_by_code, pairs), ("Bezirk", district_by_code, district_rows)):
        outgoing = {(k[0], k[1]) for k in group if k[1] != k[3]}
        incoming = {(k[2], k[3]) for k in group if k[1] != k[3]}
        vanished, appeared = [], []
        for code, states in sorted(by_code.items()):
            for i, s in enumerate(states):
                version = f"Stand {s['snapshot']}"
                if s["to"] and (i + 1 == len(states) or states[i + 1]["from"] != s["to"] + DAY) and (version, code) not in outgoing:
                    vanished.append(f"{code} (bis {s['to']})")
                if s["from"] > first and (i == 0 or states[i - 1]["to"] + DAY != s["from"]) and (version, code) not in incoming:
                    appeared.append(f"{code} (ab {s['from']})")
        findings.append(f"KL-03: {level}{'n' if level == 'Gemeinde' else 'e'}: "
                        + (f"ohne Übergang weggefallen {_examples(vanished) or '-'}; neu {_examples(appeared) or '-'}"
                           if vanished or appeared else "jeder weggefallene und jeder neue Code hat einen Übergang"))
    if unresolved:
        findings.append(f"KL-03: {len(unresolved)} Übergänge der Änderungsliste nicht in den Ständen auffindbar: {_examples(unresolved)}")
    info = {"bundesland_version": version0, "snapshots": f"{first} … {last} ({len(municipalities)} Stände)",
            "before_first": before_first}
    return rows, transitions, findings, info


# --- ÖNACE -----------------------------------------------------------------------------------

def build_oenace(conn, basic) -> tuple[list[dict], list[str], dict]:
    """klass_oenace with the versions 2003, 2008 and 2025, all levels, version-specific labels (KL-05)."""
    rows, findings, structure = [], [], {}
    for version, (valid_from, valid_to, title_file, explanation_file, levels) in OENACE.items():
        explanations, titles = defaultdict(list), []
        for r in read_text_file(conn, OENACE_DIR + explanation_file):
            if r["Ebene Erl."] != "000":
                explanations[r["EDV-Code"]].append(r["Titel/Erläuterungstext"])
            elif title_file == explanation_file:   # ÖNACE 2003: titles are the '000' rows of the COT file
                titles.append({"Ebene": r["Ebene"], "EDV-Code": r["EDV-Code"], "Code": r["Code"], "Titel": r["Titel/Erläuterungstext"]})
        if title_file != explanation_file:
            titles = read_text_file(conn, OENACE_DIR + title_file)
        parent = parents((int(r["Ebene"]), r["EDV-Code"]) for r in titles)
        structure[version] = (parent, {r["EDV-Code"]: int(r["Ebene"]) for r in titles})
        sections = dict(basic.get(f"oenace_{version}", []))
        wrong = [c for c, p in parent.items() if p and not c.startswith(p)]
        if wrong:
            findings.append(f"KL-02: ÖNACE {version}: {len(wrong)} Codes passen nicht zum übergeordneten Code: {_examples(wrong)}")
        for r in titles:
            code, level = r["EDV-Code"], int(r["Ebene"])
            label_ = sections.get(code, r["Titel"]) if level == 1 else r["Titel"]
            attr = {"ebene_nr": level, "code_anzeige": r["Code"], "quelle": OENACE_DIR + title_file}
            if label_ != r["Titel"]:
                attr["titel"] = r["Titel"]
            if r.get("Kurztitel") and r["Kurztitel"] != label_:
                attr["kurztitel"] = r["Kurztitel"]
            if explanations.get(code):
                attr["erlaeuterung"] = "\n".join(explanations[code])
            rows.append(klass_row(version, code, label_, levels[level - 1], parent[code], valid_from, valid_to, **attr))
        title_by_code = {r["EDV-Code"]: r["Titel"] for r in titles}
        for code, label_ in sections.items():
            if code == "UNB":
                rows.append(klass_row(version, code, label_, "Abschnitt", None, valid_from, valid_to, ebene_nr=1, unbekannt=True,
                                      quelle=f"klassifikationen/oenace_{version}.csv"))
            elif code not in title_by_code:
                findings.append(f"KL-02: oenace_{version}.csv: Abschnitt {code} fehlt in {title_file}")
            elif label_.casefold() != title_by_code[code].casefold():
                findings.append(f"KL-05: ÖNACE {version} {code}: Grundausstattung „{label_}“ ≠ amtlicher Titel „{title_by_code[code]}“")
    return rows, findings, structure


def build_oenace_transitions(conn, structure) -> tuple[list[dict], list[str]]:
    """Official Umsteiger (Unterklassen) and derived section transitions with their share (DQ-07, DQ-13)."""
    result, findings = [], []
    for old, new, file_name in CORRESPONDENCES:
        rel, valid_from = OENACE_DIR + file_name, OENACE[new][0]
        (p_old, l_old), (p_new, l_new) = structure[old], structure[new]
        pairs = [(r["EDV-Code"], r["korrespondierender EDV-Code"], r.get("Korrespondenz-Beschreibung") or None, r["_line"])
                 for r in read_text_file(conn, rel)]
        missing = [f"{a}→{n}" for a, n, _, _ in pairs if a not in l_old or n not in l_new]
        if missing:
            findings.append(f"KL-02: {file_name}: {len(missing)} Korrespondenzen mit Codes außerhalb der Klassifikation: {_examples(missing)}")
        types = classify_relations((a, n) for a, n, _, _ in pairs)
        result += [transition_row("klass_oenace", old, a, new, n, types[(a, n)], valid_from, f"{rel} Z{line}", text)
                   for a, n, text, line in pairs]
        # Sections; for ÖNACE 2003 also Unterabschnitte where a section has several (C: CA/CB, D: DA–DN, DQ-07).
        multi = {p for p, n in Counter(p_old[c] for c, lvl in l_old.items() if lvl == 2).items() if n > 1}
        for level_old in ((1, 2) if old == "2003" else (1,)):
            counts = Counter((ancestor(p_old, l_old, a, level_old), ancestor(p_new, l_new, n, 1)) for a, n, _, _ in pairs)
            counts = Counter({k: v for k, v in counts.items()
                              if None not in k and (level_old == 1 or p_old[k[0]] in multi)})
            totals = Counter()
            for (a, _), count in counts.items():
                totals[a] += count
            types = classify_relations(counts)
            result += [transition_row("klass_oenace", old, a, new, n, types[(a, n)], valid_from, f"abgeleitet aus {rel}",
                                      f"abgeleitet: {count} von {totals[a]} Unterklassen-Korrespondenzen", round(count / totals[a], 4))
                       for (a, n), count in sorted(counts.items())]
        if old != "2003":
            result.append(transition_row("klass_oenace", old, "UNB", new, "UNB", "1:1", valid_from,
                                         f"klassifikationen/oenace_{old}.csv, klassifikationen/oenace_{new}.csv",
                                         "Wirtschaftszweig unbekannt bleibt unbekannt", 1))
    return result, findings


# --- source mappings -------------------------------------------------------------------------

def build_mappings(conn, basic, bundesland_version: str) -> tuple[list[dict], list[tuple]]:
    """Delivery value -> code: identity from the classification files; assumptions from rule parameters."""
    rows = []
    for field, (klassifikation, periods) in FIELDS.items():
        for version, valid_from, valid_to, table in periods:
            rows += [dict(zip(MAPPING_COLUMNS, (SOURCE, field, code, klassifikation, version or bundesland_version,
                                                code, valid_from, valid_to, None))) for code, *_ in basic[table]]
    rules = conn.execute("""SELECT rule_id, status, parameters FROM ops.rule
                            WHERE action = 'source_mapping' AND status IN ('proposed', 'approved')
                            ORDER BY rule_id""").fetchall()
    for rule_id, _, parameters in rules:
        for m in parameters.get("mappings", []):
            klassifikation, periods = FIELDS[m["field"]]
            for version, valid_from, valid_to, _ in periods:
                rows += [dict(zip(MAPPING_COLUMNS, (SOURCE, m["field"], value, klassifikation,
                                                    version or bundesland_version, m["code"], valid_from, valid_to, rule_id)))
                         for value in m["source_values"]]
    duplicates = [k for k, n in Counter((r["merkmal"], r["quellwert"], r["gueltig_von"]) for r in rows).items() if n > 1]
    if duplicates:
        raise ValueError(f"Mehrdeutige Quellzuordnung (Regel kollidiert mit vorhandener Zuordnung): {_examples(duplicates)}")
    return rows, [(r[0], r[1]) for r in rules]


# --- writing, checksum, run ------------------------------------------------------------------

def copy_rows(cur, table: str, columns: tuple, rows: list[dict]) -> None:
    with cur.copy(f"COPY {table} ({', '.join(columns)}) FROM STDIN") as copy:
        for row in rows:
            copy.write_row([json.dumps(row[c], ensure_ascii=False, sort_keys=True) if c == "attribute" else row[c]
                            for c in columns])


def checksum(conn) -> str:
    """Checksum over everything the builder writes; independent of insert order and DB collation."""
    parts = [(t, "TRUE", ()) for t in KLASS_TABLES] + [
        ("klass_uebergang", "klassifikation IN ('klass_oenace', 'klass_region')", ()),
        ("quellzuordnung", "quelle = %s", (SOURCE,))]
    digest = hashlib.md5()
    for table, where, params in parts:
        value = conn.execute(f"""SELECT coalesce(md5(string_agg(t::text, E'\\n' ORDER BY t::text COLLATE "C")), '')
                                 FROM {table} t WHERE {where}""", params).fetchone()[0]
        digest.update(value.encode())
    return digest.hexdigest()


def _summary(conn, run_id: int, digest: str, info: dict, rules: list[tuple], findings: list[str]) -> str:
    lines = [f"## Klassifikationen (Lauf {run_id}, Prüfsumme {digest})", "",
             "| Klassifikation | Version | Ebene | Einträge |", "| --- | --- | --- | ---: |"]
    for k, v, e, n in conn.execute("""
            SELECT klassifikation, CASE WHEN klassifikation = 'klass_region' THEN %s ELSE version END, ebene, count(*)
            FROM klass_alle GROUP BY 1, 2, 3
            ORDER BY 1, 2, min(coalesce((attribute->>'ebene_nr')::int, 0)), 3""", (f"Zustände {info['snapshots']}",)):
        lines.append(f"| {k} | {v} | {e} | {n:,} |")
    lines += ["", "| Übergänge | Versionen | Ebene (alt) | 1:1 | 1:n | n:1 | m:n |", "| --- | --- | --- | ---: | ---: | ---: | ---: |"]
    table = defaultdict(Counter)
    for k, v, e, relation, n in conn.execute("""
            SELECT u.klassifikation, CASE WHEN u.klassifikation = 'klass_region' THEN 'Stände 2011–2026'
                                          ELSE u.version_alt || ' → ' || u.version_neu END,
                   k.ebene || CASE WHEN u.quelle LIKE 'abgeleitet%%' THEN ' (abgeleitet)' ELSE '' END, u.beziehung, count(*)
            FROM klass_uebergang u
            JOIN klass_alle k ON k.klassifikation = u.klassifikation AND k.version = u.version_alt AND k.code = u.code_alt
            GROUP BY 1, 2, 3, 4"""):
        table[(k, v, e)][relation] = n
    for (k, v, e), c in sorted(table.items()):
        lines.append(f"| {k} | {v} | {e} | " + " | ".join(f"{c.get(a, 0):,}" for a in ("1:1", "1:n", "n:1", "m:n")) + " |")
    n_mappings = conn.execute("SELECT count(*), count(regel_id) FROM quellzuordnung WHERE quelle = %s", (SOURCE,)).fetchone()
    lines += ["", f"Quellzuordnung {SOURCE}: {n_mappings[0]} Zuordnungen, davon {n_mappings[1]} aus Regeln "
                  f"({', '.join(f'{r} {label(RULE_STATUS, s)}' for r, s in rules) or 'keine'}); wirksam nur mit freigegebener Regel.",
              f"Änderungsliste: {info['before_first']} Änderungen vor dem ersten Stand nicht als Übergang übernommen.",
              "", "Befunde:"] + [f"- {b}" for b in findings]
    return "\n".join(lines)


def build(conn, log) -> str:
    """Rebuild all classifications in the caller's transaction and record the run; returns the German report."""
    basic = basic_classifications(conn)
    run_id = conn.execute("INSERT INTO ops.run (kind) VALUES ('classification') RETURNING run_id").fetchone()[0]
    log.info("classification build, run %s", run_id)
    region_rows, region_transitions, findings, info = build_region(conn, basic)
    oenace_rows, oenace_findings, structure = build_oenace(conn, basic)
    oenace_transitions, transition_findings = build_oenace_transitions(conn, structure)
    findings += oenace_findings + transition_findings
    tables = {"klass_geschlecht": build_sex(basic), "klass_qualifikation": build_qualification(basic),
              "klass_alter": build_age(), "klass_region": region_rows, "klass_oenace": oenace_rows}
    mappings, rules = build_mappings(conn, basic, info["bundesland_version"])
    category_rows, category_transitions, category_rules = build_category_level(conn, basic)
    tables["klass_qualifikation"] += category_rows
    oenace_transitions = oenace_transitions + category_transitions
    with conn.cursor() as cur:
        for table in KLASS_TABLES:
            cur.execute(f"DELETE FROM {table}")
        cur.execute("DELETE FROM klass_uebergang WHERE klassifikation IN ('klass_oenace', 'klass_region', 'klass_qualifikation')")
        cur.execute("DELETE FROM quellzuordnung WHERE quelle = %s", (SOURCE,))
        for table, rows in tables.items():
            copy_rows(cur, table, KLASS_COLUMNS, rows)
            log.info("  %s: %s entries", table, f"{len(rows):,}")
        copy_rows(cur, "klass_uebergang", TRANSITION_COLUMNS, region_transitions + oenace_transitions)
        copy_rows(cur, "quellzuordnung", MAPPING_COLUMNS, mappings)
    log.info("  klass_uebergang: %s transitions, quellzuordnung: %s mappings",
             f"{len(region_transitions) + len(oenace_transitions):,}", len(mappings))
    digest = checksum(conn)
    effective = [r for r, s in rules if s == "approved"]
    pending = [r for r, s in rules if s != "approved"]
    total = sum(map(len, tables.values())) + len(region_transitions) + len(oenace_transitions) + len(mappings)
    conn.execute("""UPDATE ops.run SET status = 'done', finished_at = now(), row_count = %s, checksum = %s, rules = %s,
                    note = %s WHERE run_id = %s""",
                 (total, digest, effective, f"Zuordnungen noch nicht wirksam (Regel nicht freigegeben): {', '.join(pending)}"
                  if pending else None, run_id))
    log.info("done: %s rows, checksum %s", f"{total:,}", digest)
    return _summary(conn, run_id, digest, info, rules, findings)


# --- check of the delivered codes ------------------------------------------------------------

CHECK_SQL = """
WITH values_ AS (
  SELECT lieferung, geschlecht, qual, oenace, bundesland, count(*) AS n,
         GROUPING(geschlecht) AS g1, GROUPING(qual) AS g2, GROUPING(oenace) AS g3, GROUPING(bundesland) AS g4
  FROM roh.lieferung
  GROUP BY GROUPING SETS ((lieferung, geschlecht), (lieferung, qual), (lieferung, oenace), (lieferung, bundesland))
), long AS (
  SELECT w.lieferung, to_date(w.lieferung || '-01', 'YYYY-MM-DD') AS month, v.field, coalesce(v.value, '') AS source_value, w.n
  FROM values_ w
  CROSS JOIN LATERAL (VALUES ('GESCHLECHT', w.geschlecht, w.g1), ('QUAL', w.qual, w.g2),
                             ('OENACE', w.oenace, w.g3), ('BUNDESLAND', w.bundesland, w.g4)) v(field, value, g)
  WHERE v.g = 0
), hits AS (
  SELECT l.*, q.klassifikation, q.version, q.code, q.regel_id,
         count(q.code) OVER (PARTITION BY l.lieferung, l.field, l.source_value) AS n_hits
  FROM long l
  LEFT JOIN quellzuordnung q ON q.quelle = %(source)s AND q.merkmal = l.field AND q.quellwert = l.source_value
   AND q.gueltig_von <= l.month AND (q.gueltig_bis IS NULL OR l.month <= q.gueltig_bis)
)
SELECT h.field, h.source_value, h.klassifikation, h.version, h.code, k.bezeichnung, h.regel_id, r.status,
       max(h.n_hits) AS n_hits,
       bool_and(k.code IS NOT NULL AND coalesce(k.gueltig_von, h.month) <= h.month
                AND coalesce(k.gueltig_bis, h.month) >= h.month) AS valid,
       min(h.lieferung), max(h.lieferung), count(DISTINCT h.lieferung), sum(h.n)
FROM hits h
LEFT JOIN klass_alle k ON k.klassifikation = h.klassifikation AND k.version = h.version AND k.code = h.code
LEFT JOIN ops.rule r ON r.rule_id = h.regel_id
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
ORDER BY 1, 4, 2
"""


def check_mappings(conn, log=None) -> str:
    """Every value of GESCHLECHT, QUAL, OENACE and BUNDESLAND in every delivery must lead to exactly one valid
    klass_ code (Phase 2 acceptance). Mappings of proposed rules are shown as waiting for approval."""
    rows = conn.execute(CHECK_SQL, {"source": SOURCE}).fetchall()
    lines = ["## Zuordnungsprüfung: gelieferte Werte → klass_-Codes (alle Lieferungen)", "",
             "| Merkmal | Wert | Ziel | Regel | Sätze | Lieferungen | Status |", "| --- | --- | --- | --- | ---: | --- | --- |"]
    totals = Counter()
    for field, value, klassifikation, version, code, label_, rule, status, n_hits, valid, first, last, n_deliveries, n in rows:
        if code is None:
            state = "nicht zuordenbar"
        elif n_hits > 1:
            state = "mehrdeutig"
        elif not valid:
            state = "Code fehlt oder nicht gültig"
        elif rule and status != "approved":
            state = f"wartet auf Freigabe {rule}"
        else:
            state = "ok"
        totals[state] += n
        target = f"{klassifikation} {version}: {code} {label_ or ''}".strip() if code else "–"
        lines.append(f"| {field} | {value or '(leer)'} | {target} | {rule or ''}{f' ({label(RULE_STATUS, status)})' if rule else ''} | "
                     f"{n:,} | {first}…{last} ({n_deliveries}) | {state} |")
    concepts = [r[0] for r in conn.execute("""SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name LIKE 'klass\\_%%' AND table_name NOT IN ('klass_uebergang', 'klass_alle')
        ORDER BY 1""")]
    total = sum(totals.values())
    met = totals["ok"] == total
    lines += ["", f"Merkmalswerte gesamt {total:,} (4 Merkmale je Satz): " + ", ".join(f"{s} {n:,}" for s, n in sorted(totals.items())),
              f"Begriffe (je eine klass_-Tabelle): {', '.join(concepts)}",
              "Abnahme: jeder gelieferte Wert führt auf genau einen gültigen klass_-Code – "
              + ("erfüllt" if met else "noch nicht erfüllt (siehe Status)")]
    if log:
        log.info("code check: %s", ", ".join(f"{s} {n:,}" for s, n in sorted(totals.items())))
    return "\n".join(lines)


def build_classifications(check_only: bool = False) -> str:
    """Build the classifications (unless `check_only`) and check the delivered codes; returns the German report."""
    log = setup_logging("klassifikation")
    parts = []
    with connect() as conn:
        if not check_only:
            with conn.transaction():
                parts.append(build(conn, log))
        parts.append(check_mappings(conn, log))
    return "\n\n".join(parts)
