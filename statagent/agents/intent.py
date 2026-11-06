"""Deterministic German intent parser (offline mode of the agents and the chat; also the safety net for the LLM).

It turns a question or instruction into tool parameters – never into numbers:
  kind        stat | explain | quality | assumptions | definition | unknown
  measure     bestand | personen | zugaenge | abgaenge | fluktuation | fluktuationsrate
  months      list of JJJJ-MM (explicit, a range, a year, or a documented default)
  dimensions  region | oenace | geschlecht | qualifikation | kategorie | alter | altersgruppe
  filters     {column: [codes]}
  rule_set    basis | auftraege
  ambiguous   terms from ops.term that need a Rückfrage (e.g. 'fluktuation')
  defaults    which documented defaults were used (printed in the card header)
"""
import re
import unicodedata

MONTHS = {"jaenner": 1, "januar": 1, "jänner": 1, "jan": 1, "feber": 2, "februar": 2, "feb": 2, "maerz": 3, "märz": 3, "mär": 3,
          "april": 4, "apr": 4, "mai": 5, "juni": 6, "jun": 6, "juli": 7, "jul": 7, "august": 8, "aug": 8, "september": 9,
          "sep": 9, "sept": 9, "oktober": 10, "okt": 10, "november": 11, "nov": 11, "dezember": 12, "dez": 12,
          "january": 1, "february": 2, "march": 3, "may": 5, "june": 6, "july": 7, "october": 10, "oct": 10, "december": 12, "dec": 12}
MONTH_NAMES = ("jänner|jaenner|januar|january|feber|februar|february|märz|maerz|march|april|mai|may|juni|june|juli|july|august|"
               "september|oktober|october|november|dezember|december|jan|feb|mär|apr|jun|jul|aug|sept|sep|okt|oct|nov|dez|dec")
BUNDESLAENDER = {"burgenland": "1", "kärnten": "2", "kaernten": "2", "niederösterreich": "3", "niederoesterreich": "3",
                 "oberösterreich": "4", "oberoesterreich": "4", "salzburg": "5", "steiermark": "6", "tirol": "7",
                 "vorarlberg": "8", "wien": "9"}
SECTION_WORDS = {"bau": "F", "baugewerbe": "F", "gastronomie": "I", "tourismus": "I", "beherbergung": "I", "handel": "G",
                 "industrie": "C", "herstellung von waren": "C", "sachgütererzeugung": "C", "landwirtschaft": "A",
                 "verkehr": "H", "finanz": "L", "gesundheit": "R", "öffentliche verwaltung": "P", "erziehung": "Q"}
SECTION_WORDS_2008 = {"finanz": "K", "gesundheit": "Q", "öffentliche verwaltung": "O", "erziehung": "P"}


UNAVAILABLE = [  # (pattern, concept) – the deliveries contain only VVH_ID, PERSON_ID, GEBURTSDATUM, GESCHLECHT, BEGINN, ENDE, QUAL, OENACE, BUNDESLAND
    (r"einkommen|gehalt|lohn|verdienst|entgelt|bezahl", "Einkommen/Entgelt"),
    (r"arbeitgeber|dienstgeber|firma|firmen|unternehmen|betrieben", "Dienstgeber (keine Dienstgeber-ID geliefert)"),
    (r"wohnort|wohnen|wohnbezirk|wohnhaft|pendl", "Wohnort (nur Bundesland des Arbeitsortes geliefert)"),
    (r"teilzeit|vollzeit|arbeitszeit|wochenstunden|geringf", "Arbeitszeit/Ausmaß der Beschäftigung"),
    (r"arbeitslos|arbeitssuch|beim ams", "Arbeitslosigkeit"),
    (r"staatsb|nationalit|herkunft|migrations|ausländ", "Staatsbürgerschaft/Herkunft"),
    (r"bildung|ausbildung|abschluss|schulabschluss|akadem", "Bildung"),
    (r"(nach|je|pro) (bezirk|gemeinde)|bezirken|gemeinden", "Bezirk/Gemeinde des Arbeitsortes (nur Bundesland geliefert)"),
]
AVAILABLE_TEXT = ("Verfügbar sind: Beschäftigungsverhältnisse oder Personen, Zu- und Abgänge, Fluktuationsrate – gegliedert nach Monat, "
                  "Bundesland (Arbeitsort), Wirtschaftszweig (ÖNACE-Abschnitt), Geschlecht, Qualifikation bzw. Arbeiter/Angestellte/Beamte, "
                  "Alter und Altersgruppen; dazu Klassifikationen (Gemeinden, Bezirke, ÖNACE) erklären und die Pensionsstatistik.")


# Words that tie a question to the delivered data. A question without any of them (and without a month of the data range)
# is outside the data – history, physics, general knowledge – and is not answered (kind "out_of_scope").
DOMAIN = re.compile(
    r"beschäft|beschaeft|arbeit|\bjobs?\b|employ|\bwork|verhältnis|verhaeltnis|\bvvh|person|menschen|leute|people|männer|maenner|"
    r"frauen|\bmen\b|women|geschlecht|gender|\bsex\b|bundesl|region|branche|wirtschaft|önace|oenace|abschnitt|sektor|\balter\b|"
    r"altersgr|altersv|altersp|altersst|\bage\b|beamte|angestellte|arbeiter|fluktuation|zugä|zugae|zugang|abgä|abgae|abgang|"
    r"lieferung|stichtag|statistik|qualitätsbericht|qualitaetsbericht|\bqb\b|gemeinde|bezirk|klassifikation|pension|rente|zählregel|"
    r"zaehlregel|datenfehler|leseregel|auffälligkeit|auffaelligkeit|österreich|oesterreich|austria|\b(" + "|".join(
        ["burgenland", "kärnten", "kaernten", "niederösterreich", "niederoesterreich", "oberösterreich", "oberoesterreich", "salzburg",
         "steiermark", "tirol", "vorarlberg", "wien", "vienna"]) + r")\b")
OUT_OF_SCOPE_TEXT = ("Diese Frage betrifft nicht die gelieferten Daten und wird deshalb nicht beantwortet. Der Agent beantwortet nur "
                     "Fragen zum Datenbestand: Beschäftigungsverhältnisse 08/2024–07/2026, Klassifikationen und die Pensionsstatistik 2018–2025.")


def in_domain(q: str, available: list[str]) -> bool:
    return bool(DOMAIN.search(q)) or bool(parse_months(q, available)[0])


PENSION_KINDS = [(r"vorzeitig", ["VAP"]), (r"korridor", ["KOR"]), (r"schwerarbeit", ["SA1", "SA2"]), (r"langzeitversichert|hackler", ["LZV"]),
                 (r"lange[rn]? versicherungsdauer", ["LVD"]), (r"witwe|witwer|hinterblieb", ["WIT"]), (r"waise", ["WAI"]),
                 (r"invalidit|berufsunf|erwerbsunf|geminderte", ["GEM"]), (r"alterspension|altersrente", ["ALTER"])]
PENSION_CARRIERS = [(r"\bpva\b|pensionsversicherungsanstalt", "PVA"), (r"\bsvs\b", "SVS"), (r"\bbvaeb\b", "BVAEB"),
                    (r"unselbständig|unselbststaendig|unselbstaendig", "PV-UNS"), (r"(?<!un)selbständig|(?<!un)selbstaendig", "PV-SELB"),
                    (r"notar", "VAN")]


def parse_pension(q: str, out: dict) -> dict:
    """Pension statistic (annual averages 2018–2025): years, dimensions and filters – never numbers."""
    years = sorted({int(y) for y in re.findall(r"\b(20(?:1[89]|2[0-5]))\b", q)})
    if len(years) >= 2 and re.search(r"\bbis\b|–|\bto\b|\bvon\b", q):
        years = list(range(years[0], years[-1] + 1))
    if not years and re.search(r"zeitreihe|entwicklung|verlauf|seit|alle jahre|trend", q):
        years = list(range(2018, 2026))
    dims, filters = [], {}
    if re.search(r"männer|maenner|frauen|geschlecht|\bmen\b|women|gender", q):
        dims.append("geschlecht")
    if re.search(r"pensionsart|nach art|arten", q):
        dims.append("pensionsart")
    if re.search(r"träger|traeger|anstalt", q) and not any(re.search(p, q) for p, _ in PENSION_CARRIERS):
        dims.append("versicherungstraeger")
    for pattern, kinds in PENSION_KINDS:
        if re.search(pattern, q):
            filters["pensionsart"] = kinds
            break
    for pattern, code in PENSION_CARRIERS:
        if re.search(pattern, q):
            filters["versicherungstraeger"] = [code]
            break
    if re.search(r"\bnur (die )?frauen\b", q):
        filters["geschlecht"], dims = ["W"], [d for d in dims if d != "geschlecht"]
    elif re.search(r"\bnur (die )?männer\b", q):
        filters["geschlecht"], dims = ["M"], [d for d in dims if d != "geschlecht"]
    out.update(kind="pension", years=years, dimensions=dims, filters=filters, months=[str(y) for y in years])
    if not years:
        out["defaults"].append("kein Jahr genannt: letztes Berichtsjahr der Pensionsstatistik")
    out["defaults"].append("Pensionen = Jahresdurchschnitt laut Meldungen der Pensionsversicherungsträger")
    return out


def norm(text: str) -> str:
    return unicodedata.normalize("NFC", text).lower().replace("ß", "ss")


def _month(y: int, m: int) -> str:
    return f"{y:04d}-{m:02d}"


def parse_months(q: str, available: list[str]) -> tuple[list[str], list[str]]:
    """Months mentioned in the question → (months, notes). Ranges are cut to the available months."""
    notes, found = [], []
    for y, m in re.findall(r"\b(20\d{2})-(0[1-9]|1[0-2])\b", q):
        found.append(_month(int(y), int(m)))
    for m, y in re.findall(r"\b(0?[1-9]|1[0-2])\s*/\s*(20\d{2})\b", q):
        found.append(_month(int(y), int(m)))
    for name, y in re.findall(rf"\b({MONTH_NAMES})\.?\s+(20\d{{2}})\b", q):
        found.append(_month(int(y), MONTHS[name]))
    for y, name in re.findall(rf"\b(20\d{{2}})\s+(?:im |in |in the month of )?({MONTH_NAMES})\b", q):   # "2026 in june"
        found.append(_month(int(y), MONTHS[name]))
    is_range = bool(re.search(r"\b(bis|–|-)\b", q)) and len(found) >= 2 or ("von" in q and "bis" in q and len(found) >= 2)
    if is_range:
        lo, hi = min(found), max(found)
        return [m for m in available if lo <= m <= hi], notes
    if found:
        return sorted(set(found)), notes
    years = sorted(set(re.findall(r"\b(202[4-6])\b", q)))
    if years:
        months = [m for m in available if m[:4] in years]
        if months and len(months) < 12 * len(years):
            notes.append(f"Jahr {', '.join(years)}: vorhanden sind {months[0]} bis {months[-1]}")
        return months, notes
    if re.search(r"zeitreihe|entwicklung|verlauf|nach monat|monatlich|je monat|alle monate|über die zeit|seit beginn|trend", q):
        return list(available), notes
    if re.search(r"vormonat|letzten monat", q):
        return available[-2:-1], notes
    return [], notes


def parse(question: str, available: list[str]) -> dict:
    q = norm(question)
    out = {"question": question, "kind": "stat", "measure": "bestand", "months": [], "dimensions": [], "filters": {},
           "rule_set": "basis", "ambiguous": [], "defaults": [], "notes": [], "chart": None}

    # --- metadata and QA intents ------------------------------------------------------------
    code_region = re.search(r"\b(gemeinde|bezirk|region|gemeindekennziffer)\s*(\d{1,5})\b", q)
    code_oenace = re.search(r"\b(?:önace|oenace|abschnitt|wirtschaftszweig|branche)[- ]*(?:abschnitt\s*)?([a-v](?:\s?\d{2}(?:\.\d{1,2}(?:-\d)?)?)?)\b", q)
    explain_words = re.search(r"erklär|erklaer|was ist aus|geworden|übergang|uebergang|was bedeutet|was ist (der|die|das)? ?(code|gemeinde|abschnitt)|zusammengelegt|geteilt|historie", q)
    if code_region and re.fullmatch(r"(19|20)\d\d", code_region.group(2)) and not explain_words:
        code_region = None                                   # "nach Bezirk 2025" is a year, not a code
    if code_region and (explain_words or "gemeinde" in q or "bezirk" in q):
        out.update(kind="explain", klass="region", code=code_region.group(2), version=None)
        return out
    if code_oenace and explain_words:
        code = code_oenace.group(1).upper().replace("  ", " ")
        version = "2025" if "2025" in q and "2008" not in q else ("2008" if ("geworden" in q or "2008" in q or "aus" in q) else None)
        out.update(kind="explain", klass="oenace", code=code, version=version)
        return out
    month_any, _ = parse_months(q, available)
    if re.search(r"qualitätsbericht|qualitaetsbericht|\bqb\b", q):
        out.update(kind="quality", months=month_any[-1:] or available[-1:])
        if not month_any:
            out["defaults"].append(f"letzter Berichtsmonat {available[-1]}")
        return out
    if re.search(r"annahme|leseregel|regeln gelten|auffälligkeit|auffaelligkeit|datenfehler|fehler in|probleme", q):
        out.update(kind="assumptions", months=month_any[-1:] or available[-1:])
        return out
    if re.search(r"wie wird .*gezählt|zählregel|zaehlregel|definition|was zählt als|was gilt als beschäftigt", q):
        out["kind"] = "definition"
        return out

    # --- feasibility: concepts that are not in the deliveries (SW-05) --------------------------
    for pattern, concept in UNAVAILABLE:
        if concept.startswith("Dienstgeber") and re.search(r"wechsel|fluktuation", q):
            continue                                         # "Arbeitgeber wechseln" = Fluktuation, answerable
        if re.search(pattern, q):
            out.update(kind="unavailable", missing=concept)
            return out

    # --- outside the data / pension statistic ------------------------------------------------
    if not in_domain(q, available):
        out["kind"] = "out_of_scope"
        return out
    if re.search(r"pension|\brente|ruhestand|pensionist", q):
        return parse_pension(q, out)

    # --- statistic ------------------------------------------------------------------------
    if "fluktuationsrate" in q:
        out["measure"] = "fluktuationsrate"
    elif "fluktuation" in q or "wechsel" in q and "arbeitgeber" in q:
        out["ambiguous"].append("fluktuation")
    elif re.search(r"zugänge|zugaenge|zugang|neue verhältnisse|eintritte|neu begonnen", q):
        out["measure"] = "zugaenge"
    elif re.search(r"abgänge|abgaenge|abgang|beendet|austritte", q):
        out["measure"] = "abgaenge"
    if re.search(r"\bpersonen\b|\bmenschen\b|köpfe|koepfe", q) and out["measure"] == "bestand":
        out["measure"] = "personen"
    if re.search(r"ganzen? monat|mindestens einen tag|im laufe des monats|monatsbeschäftigung", q):
        out["rule_set"] = "auftraege"
    elif "nach den änderungsaufträgen" in q or "neue regel" in q or "auftraege" in q:
        out["rule_set"] = "auftraege"

    dims = []
    if re.search(r"männer|maenner|frauen|geschlecht|\bm/w\b|weiblich|männlich|\bmen\b|women|gender|\bsex\b", q) or "pyramide" in q:
        dims.append("geschlecht")
    if re.search(r"bundesl(a|ä)nd|nach region|regional|je land", q):
        dims.append("region")
    if re.search(r"wirtschaftszweig|wirtschaftsbereich|branche|önace|oenace|sektor|abschnitt", q):
        dims.append("oenace")
    if re.search(r"altersgruppe|5-jahres|fünfjahres|fuenfjahres", q):
        dims.append("altersgruppe")
    elif re.search(r"alter|altersverteilung|altersstruktur|alterspyramide", q):
        dims.append("alter")
    if re.search(r"altersverteilung|alterspyramide|altersstruktur", q) and "geschlecht" not in dims:
        dims.append("geschlecht")      # shown as a population pyramid
    if re.search(r"qualifikation|beschäftigungskategorie|beschaeftigungskategorie|dienstvertrag|freie dienstverträge|\bfd\b", q):
        dims.append("qualifikation")
    elif re.search(r"arbeiter.*angestellte|angestellte.*arbeiter|kategorie", q):
        dims.append("kategorie")
        out["defaults"].append("Arbeiter/Angestellte inkl. freier Dienstverträge (wie im Beispielbericht)")

    filters: dict[str, list[str]] = {}
    for name, code in BUNDESLAENDER.items():
        if re.search(rf"\b{name}\b", q):
            if "region" in dims and not re.search(rf"\b(in|für|fuer) {name}\b", q):
                continue
            filters.setdefault("region", [])
            if code not in filters["region"]:
                filters["region"].append(code)
    if "beamte" in q and "kategorie" not in dims and "qualifikation" not in dims:
        filters["qualifikation"] = ["Beamte"]
    if re.search(r"freie dienstverträge|freien dienstverträge|freie dienstnehmer", q) and "qualifikation" not in dims:
        filters["qualifikation"] = ["ArbeiterFD", "AngestellteFD"]
    if re.search(r"\bnur (die )?frauen\b|\bvon frauen\b", q) and "geschlecht" in dims and "männer" not in q:
        filters["geschlecht"] = ["W"]
        dims.remove("geschlecht")
    if re.search(r"\bnur (die )?männer\b", q) and "geschlecht" in dims and "frauen" not in q:
        filters["geschlecht"] = ["M"]
        dims.remove("geschlecht")
    sec = re.search(r"abschnitt\s+([a-v])\b", q)
    if sec and "oenace" in dims:
        filters["oenace"] = [sec.group(1).upper()]
        dims.remove("oenace")
    out["dimensions"], out["filters"] = dims, filters

    months, notes = parse_months(q, available)
    out["notes"] += notes
    if not months:
        if re.search(r"aktuell|derzeit|jetzt|zuletzt|neueste|letzte", q):
            out["defaults"].append(f"„aktuell“ = letzter veröffentlichter Berichtsmonat {available[-1]}")
        else:
            out["defaults"].append(f"kein Zeitraum genannt: letzter Berichtsmonat {available[-1]}")
        months = available[-1:]
    out["months"] = months
    if out["measure"] in ("zugaenge", "abgaenge", "fluktuation", "fluktuationsrate") and months and months[0] == available[0]:
        months = months[1:]
        out["months"] = months
        out["notes"].append(f"{available[0]}: kein Vormonat im Datenbestand – Zu-/Abgänge ab {available[1]}")
    if out["measure"] == "bestand" and not out["ambiguous"]:
        out["defaults"].append("Beschäftigte = Versicherungsverhältnisse (Zählregel Z1)")
    if "region" in dims or "region" in filters:
        out["defaults"].append("Bundesland des Arbeitsortes (Wohnort nicht geliefert)")
    if out["rule_set"] == "basis":
        out["defaults"].append("Stichtag Monatsletzter (Regelwerk Basis)")
    if not re.search(r"\d|beschäft|beschaeft|verhältnis|personen|zahl|wie viele|anzahl|statistik|zeitreihe|entwicklung|verteilung|"
                     r"fluktuation|zugä|abgä|männer|frauen|bundesl|branche|wirtschaft|alter|beamte|arbeiter|angestellte|"
                     r"employ|work|people|\bmen\b|women|how many", q):
        out["kind"] = "unknown"
    return out


def merge_follow_up(new: dict, previous: dict | None, question: str) -> dict:
    """Follow-up questions ("und nach Bundesland?", "nur Frauen", "und im Juni 2026?") refine the previous card."""
    if not previous or previous.get("kind") != "stat" or new.get("kind") not in ("stat", "unknown", "out_of_scope"):
        return new
    q = norm(question).strip()
    follow = q.startswith(("und ", "nur ", "jetzt ", "dasselbe", "das gleiche", "gleich ", "auch ", "wie ist es", "und?", "aber ")) or len(q.split()) <= 4
    if not follow:
        return new
    merged = dict(previous)
    merged["question"] = question
    merged["kind"] = "stat"
    merged["defaults"] = [d for d in previous.get("defaults", []) if not d.startswith("kein Zeitraum")]
    explicit_months, _ = parse_months(q, [])
    if new["months"] and (explicit_months or re.search(r"20\d{2}|zeitreihe|entwicklung|verlauf", q)):
        merged["months"] = new["months"]
    if new["dimensions"]:
        prev_dims = list(previous.get("dimensions", []))
        merged["dimensions"] = (prev_dims + [d for d in new["dimensions"] if d not in prev_dims]) if q.startswith("und") \
            else new["dimensions"]
    if new["filters"]:
        merged["filters"] = {**previous.get("filters", {}), **new["filters"]}
        for k in new["filters"]:
            if k in merged["dimensions"]:
                merged["dimensions"] = [d for d in merged["dimensions"] if d != k]
    if new["measure"] != "bestand" or new["ambiguous"]:
        merged["measure"], merged["ambiguous"] = new["measure"], new["ambiguous"]
    if new["rule_set"] != "basis":
        merged["rule_set"] = new["rule_set"]
    merged["follow_up"] = True
    return merged


# --- instructions for the agents (change orders and live changes) -------------------------------

def parse_instruction(text: str, available: list[str]) -> dict:
    q = norm(text)
    out = {"instruction": text, "intent": "unknown", "role": "Koordination", "params": {}}
    # carry out what a person has approved: „Setze die freigegebenen Aufträge um“, „Freigegebene Aufträge umsetzen“, „Führe … aus“
    if re.search(r"\bsetzt?e?\b.*\bum\b|umsetz|freigegeben\w*\s+(auftr|regel|änderung|aenderung)|f(ü|ue)hre?\b.*\baus\b|ausf(ü|ue)hren|"
                 r"\bexecute\b|\bapply\b|carry out", q) and not re.search(r"\bprobe\b|vorschau", q) \
            and ("freigegeben" in q or not re.search(r"auftrag\s*[123]\b|ministerium|ganze[sn]? monat|dienstvertr|sonderauswertung", q)):
        # „Setze Änderungsauftrag 1 um“ GIVES order 1 (proposal); only approved or unspecified orders are carried out
        out.update(intent="execute", role="Koordination", params={})
        return out
    if re.search(r"auftrag\s*1\b|freie[nr]? dienstvertr|dv und fd|dienstvertrag und freie|nur noch arbeiter|nicht mehr zwischen dienstvertrag", q):
        out.update(intent="order1", role="Klassifikation",
                   params={"version": "Beschaeftigungskategorie", "valid_from": "2024-08-01"})
    elif re.search(r"auftrag\s*2\b|ganzes? monat|ganzen monat|statt stichtag|mindestens einen tag|einziger tag", q):
        out.update(intent="order2", role="Datenmanagement", params={})
    elif re.search(r"auftrag\s*3\b|ministerium", q):
        months, _ = parse_months(q, available)
        days = re.search(r"(\d{2,3})\s*tage", q)
        out.update(intent="order3", role="Reporting",
                   params={"report_month": months[-1] if months else "2026-07", "months": 12,
                           "min_days": int(days.group(1)) if days else 200, "quals": ["ArbeiterDV", "ArbeiterFD"],
                           "oenace": "C", "incomplete_deliveries": ["2025-10"], "max_age": 110})
    else:
        spec = parse_special(q, available)
        if spec:
            out.update(intent="special", role="Reporting", params=spec)
        elif re.search(r"prüfe|pruefe|kontrolliere|qualität|auffällig", q):
            months, _ = parse_months(q, available)
            out.update(intent="check", role="Qualitätssicherung", params={"months": months[-1:] or available[-1:]})
        elif re.search(r"lauf|neu rechnen|rechne|gesamtlauf", q):
            months, _ = parse_months(q, available)
            out.update(intent="run", role="Datenmanagement",
                       params={"months": months or available, "rule_set": "auftraege" if "auftr" in q or "neue" in q else "basis"})
        elif re.search(r"erklär|erklaer|übergang|klassifikation", q):
            out.update(intent="explain", role="Klassifikation", params={})
    return out


def parse_special(q: str, available: list[str]) -> dict | None:
    """Live change by language → parameters of a generated special evaluation (Sonderauswertung, T6)."""
    groups, filters, exclude, labels, age_bounds = [], {}, {}, [], []
    explicit_bands = re.search(r"\b\d{1,3}\s*(?:-|–|bis)\s*\d{1,3}\b", q)
    if re.search(r"5[- ]?jahres|fünfjahres|fuenfjahres|5-jahres-alter|fünf jahre", q) or ("altersgruppen" in q and not explicit_bands):
        groups.append("altersgruppe5")
        labels.append("Altersgruppen zu 5 Jahren")
    if re.search(r"10[- ]?jahres|zehnjahres", q):
        groups.append("altersgruppe10")
        labels.append("Altersgruppen zu 10 Jahren")
    bands = re.findall(r"\b(\d{1,3})\s*(?:-|–|bis)\s*(\d{1,3})\b", q)
    over = re.search(r"\b(\d{1,3})\s*(?:\+|und (?:älter|mehr|darüber)|plus)", q)
    if "alter" in q and (bands or over) and "altersgruppe5" not in groups and "altersgruppe10" not in groups:
        bounds = sorted({int(a) for a, _ in bands} | {int(b) + 1 for _, b in bands} | ({int(over.group(1))} if over else set()))
        bounds = [b for b in bounds if 1 <= b <= 110]
        if bounds:
            groups.append("altersbaender")
            labels.append("Altersgruppen " + ", ".join(f"{a}–{b}" for a, b in bands) + (f", {over.group(1)} und älter" if over else ""))
            age_bounds = bounds
    if re.search(r"arbeiter,? angestellte (und|,) beamte|nach kategorie|beschäftigungskategorie", q):
        groups.append("kategorie")
        labels.append("nach Arbeiter/Angestellte/Beamte")
    if re.search(r"wien (separat|getrennt|gesondert|extra|eigens|einzeln)|wien und (den )?rest|wien vs|ohne wien", q) or \
            re.search(r"(separat|getrennt|gesondert)[^.]*wien", q):
        if re.search(r"ohne wien", q):
            exclude["region"] = ["9"]
            labels.append("ohne Wien")
        else:
            groups.append("wien_rest")
            labels.append("Wien gesondert, übriges Österreich zusammen")
    m = re.search(r"(ohne|exklusive|exkl\.?|ausschlie(ss|ß)en|nicht mitzählen|nicht zählen)\s+(die\s+)?(beamte|beamten|freie dienstverträge|fd|arbeiter|angestellte)", q) \
        or re.search(r"(beamte|beamten)\s+(ausschlie(ss|ß)en|weglassen|herausnehmen|nicht zählen)", q)
    if m:
        what = m.group(0)
        if "beamte" in what:
            exclude["qualifikation"] = ["Beamte"]
            labels.append("ohne Beamte")
        elif "freie" in what or " fd" in what:
            exclude["qualifikation"] = ["ArbeiterFD", "AngestellteFD"]
            labels.append("ohne freie Dienstverträge")
        elif "arbeiter" in what:
            exclude["qualifikation"] = ["ArbeiterDV", "ArbeiterFD"]
            labels.append("ohne Arbeiter")
        elif "angestellte" in what:
            exclude["qualifikation"] = ["AngestellteDV", "AngestellteFD"]
            labels.append("ohne Angestellte")
    m_sex = re.search(r"\bnur (die )?(frauen|männer)\b", q)
    if m_sex:
        filters["geschlecht"] = ["W" if m_sex.group(2) == "frauen" else "M"]
        labels.append(f"nur {m_sex.group(2).capitalize()}")
    for name, code in BUNDESLAENDER.items():
        if re.search(rf"\bnur (in )?{name}\b", q) and code not in filters.get("region", []):
            filters.setdefault("region", []).append(code)
            labels.append(f"nur {name.capitalize()}")
    m_cat = re.search(r"\bnur (die )?(arbeiter|angestellten|angestellte|beamte|beamten)\b", q)
    if m_cat:
        c = m_cat.group(2)
        filters["qualifikation"] = (["ArbeiterDV", "ArbeiterFD"] if c.startswith("arbeiter") else
                                    ["AngestellteDV", "AngestellteFD"] if c.startswith("angestellte") else ["Beamte"])
        labels.append(f"nur {c.capitalize()}")
    for word, dim in (("geschlecht", "geschlecht"), ("männer und frauen", "geschlecht"), ("bundesland", "region"),
                      ("wirtschaftszweig", "oenace"), ("branche", "oenace"), ("önace", "oenace"), ("qualifikation", "qualifikation")):
        if word in q and dim not in groups and not (dim == "region" and "wien_rest" in groups):
            groups.append(dim)
    if not labels:
        return None
    months, _ = parse_months(q, available)
    out = {"group_by": groups or ["insgesamt"], "filters": filters, "exclude": exclude, "months": months or available,
           "rule_set": "auftraege" if re.search(r"auftr|ganzes monat|neue regeln", q) else "basis", "label": ", ".join(labels)}
    if "altersbaender" in groups:
        out["age_bounds"] = age_bounds
    return out
