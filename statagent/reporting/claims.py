"""Claim check (PRD §5.1): every number in an answer text must come from the tool result it is based on.

Before a text is shown, all numeric tokens are extracted. Allowed are
  - values of the result (`numbers` of the tool envelope, plus derived values registered by the deterministic
    renderer: sums, differences, shares), in German or plain formatting, also rounded as rendered (1 decimal for %)
  - context tokens that are not statistics: dates and months of the request, years, rule/problem IDs (R-DQ01, DQ-02,
    Z1), classification codes and versions named in the parameters
Anything else fails the check; the caller then falls back to the template text or abstains ("nicht prüfbar").
"""
import re

NUMBER = re.compile(r"(?<![\w.,-])[-+−]?\d{1,3}(?:\.\d{3})+(?:,\d+)?(?![\w])|(?<![\w.,-])[-+−]?\d+(?:,\d+)?(?![\w.])|(?<![\w.,-])[-+−]?\d+\.\d+(?![\w])")
SAFE_PATTERNS = [
    re.compile(r"\b\d{1,2}\.\d{1,2}\.20\d{2}\b"),            # 31.07.2026
    re.compile(r"\b20\d{2}-\d{2}(?:-\d{2})?\b"),              # 2026-07, 2026-07-31
    re.compile(r"\b\d{1,2}/20\d{2}\b"),                        # 07/2026
    re.compile(r"\b(?:R|RF)-[A-Z]{1,3}\d{1,3}\b"),              # R-DQ01, RF-DQ02, R-A1
    re.compile(r"\b(?:DQ|RD|KL|PEN|ENV|SPEC|T|Z)-?\d{1,2}\b"),  # DQ-02, RD-01, Z1, T7
    re.compile(r"\bÖNACE\s?20(?:03|08|25)\b"),
    re.compile(r"\b[A-V]\s?\d{2}\.\d{1,2}(?:-\d)?\b"),         # ÖNACE codes like C 10.71
    re.compile(r"\bLauf\s\d+\b"),                               # run IDs are evidence references
    re.compile(r"\bC-\d{4}\b"),
]


def parse_number(token: str) -> float | None:
    t = token.replace("−", "-").replace("+", "")
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", t):
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def _years_and_context(context: dict) -> set[float]:
    ok = set()
    for m in context.get("months", []):
        y, mo = m.split("-")
        ok |= {float(y), float(int(mo))}
    for v in context.get("extra", []):
        ok.add(float(v))
    ok |= {float(y) for y in range(2003, 2031)}   # years are context, not statistics
    return ok


def check(text: str, numbers, context: dict | None = None) -> dict:
    """Returns {passed, checks, numbers_checked, details}. `numbers` = allowed result values."""
    context = context or {}
    allowed = set()
    for n in numbers or []:
        try:
            f = float(n)
        except (TypeError, ValueError):
            continue
        allowed |= {f, round(f, 1), round(f, 2), abs(f), round(abs(f), 1)}
    safe_text = text
    for label_ in sorted(context.get("labels", []), key=len, reverse=True):   # category labels such as „53 Jahre“, „15–19“
        if label_ and any(ch.isdigit() for ch in label_):
            safe_text = safe_text.replace(label_, " ")
    safe_hits = 0
    for pat in SAFE_PATTERNS:
        safe_hits += len(pat.findall(safe_text))
        safe_text = pat.sub(" ", safe_text)
    ctx = _years_and_context(context)
    details, failed = [], 0
    for token in NUMBER.findall(safe_text):
        value = parse_number(token)
        if value is None:
            continue
        if value in allowed or abs(value) in allowed:
            details.append({"token": token, "ok": True, "source": "Ergebnis der Abfrage"})
        elif value in ctx and value == int(value) and (value >= 2003 or value <= 12):
            details.append({"token": token, "ok": True, "source": "Zeitangabe der Anfrage"})
        else:
            failed += 1
            details.append({"token": token, "ok": False, "source": "nicht im Ergebnis"})
    numbers_checked = sum(1 for d in details if d["source"] == "Ergebnis der Abfrage") + failed
    return {"passed": failed == 0, "checks": len(details) + safe_hits, "numbers_checked": numbers_checked,
            "failed": failed, "details": details}
