"""Which files and tables an answer used ("Verwendete Dateien") – so a user can open and check them again.

Package files come from the register roh.file (path + SHA-256 at load time); generated files (quality reports)
are hashed from disk. Purely deterministic: derived from the tool parameters, never from a language model.
"""
import hashlib

from statagent.config import BASE_DIR

DIM_FILES = {  # dimension/filter → classification files that define its codes and labels
    "region": ["klassifikationen/bundesland.csv", "klassifikationen/regionen/bundeslaender.csv"],
    "geschlecht": ["klassifikationen/geschlecht.csv"],
    "qualifikation": ["klassifikationen/qualifikation.csv"],
    "kategorie": ["klassifikationen/qualifikation.csv"],
}
DIM_TABLES = {"region": "klass_region", "oenace": "klass_oenace", "geschlecht": "klass_geschlecht", "qualifikation": "klass_qualifikation",
              "kategorie": "klass_qualifikation", "alter": "klass_alter", "altersgruppe": "klass_alter", "altersgruppe10": "klass_alter",
              "pensionsart": "klass_pensionsart", "versicherungstraeger": "klass_versicherungstraeger"}


def _register(conn, where: str, params=()) -> list[tuple[str, str, str]]:
    return conn.execute(f"SELECT path, sha256, area FROM roh.file WHERE {where} AND path NOT LIKE '%%LIESMICH%%' ORDER BY path",
                        params).fetchall()


def _generated(path: str, role: str) -> dict | None:
    f = BASE_DIR / path
    if not f.exists():
        return None
    return {"path": path, "sha256": hashlib.sha256(f.read_bytes()).hexdigest(), "area": "abgabe", "role": role, "generated": True}


def sources_for(conn, p: dict, card: dict) -> dict:
    kind = p.get("kind", "stat")
    files: list[dict] = []
    tables: list[str] = []

    def add(rows, role):
        for path, sha, area in rows:
            if not any(f["path"] == path for f in files):
                files.append({"path": path, "sha256": sha, "area": area, "role": role})

    params = card.get("params") or p
    months = params.get("months") or p.get("months") or []
    dims = list(params.get("dimensions") or []) + list((params.get("filters") or {}).keys())
    if kind == "stat":
        rule_set = params.get("rule_set", "basis")
        add(_register(conn, "area = 'lieferungen' AND substring(path from 'lieferung_(\\d{4}-\\d{2})') = ANY(%s)", (months,)),
            "Monatslieferung (Rohdaten, über den Monatslauf gelesen)")
        for d in dims:
            if d in DIM_FILES:
                add(_register(conn, "path = ANY(%s)", (DIM_FILES[d],)), f"Klassifikation ({d})")
            if d == "oenace":
                wanted = (["klassifikationen/oenace_2008.csv"] if any(m <= "2024-12" for m in months) else []) + \
                         (["klassifikationen/oenace_2025.csv"] if any(m >= "2025-01" for m in months) else [])
                add(_register(conn, "path = ANY(%s)", (wanted,)), "Klassifikation ÖNACE")
        for m in months:
            qb = _generated(f"abgabe/qualitaetsberichte/{rule_set}/QB_{m}.md", f"Qualitätsbericht {m} (erzeugt)")
            if qb:
                files.append(qb)
        measure = params.get("measure", "bestand")
        tables += ["store.month_record"] if measure == "personen" else (["stat_beschaeftigte"] if measure == "bestand"
                                                                        else ["store.month_flow", "stat_beschaeftigte"])
        tables += ["ops.run", "ops.rule"]
        if (card.get("quality") or {}).get("handling"):
            tables.append("work.dq_copy")
    elif kind == "pension":
        for f in (card.get("evidence") or {}).get("pension_files", []):
            files.append({"path": f["file"], "sha256": f["sha256"], "area": "pensionen", "role": "Meldung eines Pensionsversicherungsträgers"})
        tables += ["stat_pensionen", "klass_pensionsart", "klass_versicherungstraeger"]
    elif kind == "explain":
        if p.get("klass") == "region":
            add(_register(conn, "area = 'klassifikationen' AND path LIKE 'klassifikationen/regionen/%%'"),
                "Regionalklassifikation und Änderungslisten")
            tables += ["klass_region", "klass_uebergang", "quellzuordnung"]
        else:
            add(_register(conn, "area = 'klassifikationen' AND (path LIKE 'klassifikationen/oenace%%')"), "ÖNACE-Klassifikation und Umsteiger")
            tables += ["klass_oenace", "klass_uebergang", "quellzuordnung"]
    elif kind in ("quality", "assumptions"):
        add(_register(conn, "area = 'lieferungen' AND substring(path from 'lieferung_(\\d{4}-\\d{2})') = ANY(%s)", (months,)),
            "Monatslieferung (geprüft)")
        for m in months:
            qb = _generated(f"abgabe/qualitaetsberichte/basis/QB_{m}.md", f"Qualitätsbericht {m} (erzeugt)")
            if qb:
                files.append(qb)
        tables += ["ops.finding", "ops.rule", "ops.run"]
    elif kind == "definition":
        tables += ["variable", "statistik_beschreibung"]
    for d in dims:
        if d in DIM_TABLES and DIM_TABLES[d] not in tables:
            tables.append(DIM_TABLES[d])
    return {"files": files, "tables": list(dict.fromkeys(tables))}
