"""Database backup and restore (SW-19): the local database is not in git (10 GB, GitHub allows 100 MB per file).

`sichern` writes a compressed custom-format dump (pg_dump -Fc) of the whole database – delivered raw data, versioned
store, results, approvals, publications, runs, answer log – plus its SHA-256 into `sicherung/` (ignored by git).
`wiederherstellen DATEI --ja` loads it into the configured database (replaces its content; a person confirms with --ja),
checks the SHA-256 first and runs ANALYZE afterwards. Share the dump outside git (USB, SV-Box, release asset).
The delivered package files are not touched; `pruefen` afterwards proves the restored rows match the files.
"""
import datetime as dt
import hashlib
import os
import shutil
import subprocess
from pathlib import Path

from statagent.config import BASE_DIR, connect

DIR = BASE_DIR / "sicherung"
PG_BIN = Path(r"C:\Program Files\PostgreSQL\16\bin")


def _tool(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    exe = PG_BIN / f"{name}.exe"
    if exe.exists():
        return str(exe)
    raise RuntimeError(f"{name} nicht gefunden – PostgreSQL-bin-Ordner in den PATH aufnehmen")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def backup(target: Path | None = None) -> dict:
    DIR.mkdir(exist_ok=True)
    db = os.environ.get("PGDATABASE", "statistik")
    out = target or DIR / f"{db}_{dt.datetime.now():%Y-%m-%d_%H%M}.dump"
    subprocess.run([_tool("pg_dump"), "-Fc", "-Z", "6", "--no-owner", "--no-privileges", "-f", str(out), db], check=True)
    sha = _sha256(out)
    out.with_suffix(out.suffix + ".sha256").write_text(f"{sha}  {out.name}\n", encoding="utf-8")
    with connect() as conn:
        rows = conn.execute("SELECT count(*) FROM roh.lieferung").fetchone()[0]
        conn.execute("INSERT INTO ops.change_log (instruction, change, object) VALUES (%s, %s, %s)",
                     ("Datenbank sichern", f"Sicherung {out.name} ({out.stat().st_size / 1e9:.2f} GB, SHA-256 {sha[:16]}…, "
                                           f"{rows:,} Lieferzeilen)", f"backup:{out.name}"))
    return {"path": out, "bytes": out.stat().st_size, "sha256": sha}


def restore(path: Path, jobs: int = 4) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    expected = path.with_suffix(path.suffix + ".sha256")
    sha = _sha256(path)
    if expected.exists() and expected.read_text(encoding="utf-8").split()[0] != sha:
        raise ValueError("SHA-256 der Sicherung stimmt nicht mit der .sha256-Datei überein – Datei beschädigt?")
    db = os.environ.get("PGDATABASE", "statistik")
    subprocess.run([_tool("pg_restore"), "--clean", "--if-exists", "--no-owner", "--no-privileges", "-j", str(jobs), "-d", db, str(path)],
                   check=True)
    with connect() as conn:
        conn.execute("ANALYZE")
        months = conn.execute("SELECT count(DISTINCT stand) FROM stat_beschaeftigte").fetchone()[0]
        conn.execute("INSERT INTO ops.change_log (instruction, change, object) VALUES (%s, %s, %s)",
                     ("Datenbank wiederherstellen", f"Sicherung {path.name} (SHA-256 {sha[:16]}…) eingespielt", f"backup:{path.name}"))
    return {"sha256": sha, "stands": months}
