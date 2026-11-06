"""German labels for the English enum values of the ops schema (everything users see is German)."""
RULE_STATUS = {"proposed": "vorgeschlagen", "approved": "freigegeben", "rejected": "abgelehnt", "retired": "außer Kraft"}
RULE_TYPE = {"reading": "Einleseregel", "check": "Prüfregel", "counting": "Zählregel", "mapping": "Zuordnungsregel"}
DECISION = {"approved": "freigegeben", "rejected": "abgelehnt"}
RUN_KIND = {"store": "Bestand", "month": "Monatslauf", "classification": "Klassifikationen"}
RUN_STATUS = {"running": "läuft", "done": "fertig", "failed": "Fehler"}


def label(mapping: dict, value: str | None) -> str:
    return mapping.get(value, value or "")


RULE_SET = {"basis": "Basis", "auftraege": "Aufträge"}   # stored values stay basis/auftraege (DB, API, file names)


def rule_set_label(value: str | None) -> str:
    return RULE_SET.get(value or "", value or "–")
