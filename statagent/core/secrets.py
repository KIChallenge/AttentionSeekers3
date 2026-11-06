"""Secret scan (ENV-08, Phase 8): the whole git history and the working tree must not contain credentials.

Checks for the SV-BOX password, Azure/OpenAI keys, private keys and passwords other than the package's public default
database password 'statistik'. The pattern for the SV-BOX password is derived from the (gitignored) task document if it is
present, so the password itself is never written into the repository.
"""
import re
import subprocess

from statagent.config import BASE_DIR

PATTERNS = {
    "API-Schlüssel (Agent/Azure/OpenAI/Anthropic/Gemini)": re.compile(
        r"(AZURE_OPENAI_API_KEY|AGENT_API_KEY)[ \t]*=[ \t]*[A-Za-z0-9_\-]{8,}|\bsk-(ant-)?[A-Za-z0-9_\-]{20,}|\bAIza[0-9A-Za-z_\-]{30,}"),
    "privater Schlüssel": re.compile(r"-----BEGIN (RSA |OPENSSH |EC |)PRIVATE KEY-----"),
    "Passwort (außer Standard „statistik“)": re.compile(r"(PGPASSWORD|PASSWORD|PASSWORT)\s*[=:]\s*(?!statistik\b)[^\s'\"]{4,}", re.I),
    "SV-BOX-Freigabelink": re.compile(r"svbox\.at/s/[A-Za-z0-9]+"),
}


def _svbox_password() -> str | None:
    doc = BASE_DIR / "SV md files" / "Use Case 3 StatAgent.md"
    if doc.is_file():
        m = re.search(r"PW:\s*`([^`]+)`", doc.read_text(encoding="utf-8", errors="replace"))
        return m.group(1) if m else None
    return None


def scan() -> list[tuple[str, str]]:
    patterns = dict(PATTERNS)
    pw = _svbox_password()
    if pw:
        patterns["SV-BOX-Passwort"] = re.compile(re.escape(pw))
    history = subprocess.run(["git", "log", "--all", "-p", "--no-color"], cwd=BASE_DIR, capture_output=True, text=True,
                             encoding="utf-8", errors="replace").stdout
    tracked = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=BASE_DIR, capture_output=True, text=True).stdout.split("\n")
    hits = []
    for name, pat in patterns.items():
        for m in pat.finditer(history):
            line = history[history.rfind("\n", 0, m.start()) + 1: history.find("\n", m.end())]
            hits.append((name, "git-Historie: " + line.strip()[:80].replace(m.group(0), "***")))
    for rel in tracked:
        path = BASE_DIR / rel
        if not rel or not path.is_file() or rel.startswith(("lieferungen/", "klassifikationen/", "pensionen/")) or path.stat().st_size > 5_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for name, pat in patterns.items():
            if pat.search(text):
                hits.append((name, f"Datei {rel}"))
    return hits
