"""Database schema: the delivered 01_schema.sql (unchanged, once) plus our sql/*.sql files.

All files in sql/ are idempotent (IF NOT EXISTS / ON CONFLICT DO NOTHING) and run in name order.
"""
from statagent.config import PACKAGE_SCHEMA, SQL_DIR


def migrate(conn) -> list[str]:
    applied = []
    if not conn.execute("SELECT to_regclass('roh.lieferung') IS NOT NULL").fetchone()[0]:
        conn.execute(PACKAGE_SCHEMA.read_text(encoding="utf-8"))
        applied.append(PACKAGE_SCHEMA.name)
    for path in sorted(SQL_DIR.glob("*.sql")):
        conn.execute(path.read_text(encoding="utf-8"))
        applied.append(path.name)
    return applied
