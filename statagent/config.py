"""Paths and database connection settings.

Connection parameters come from the environment (``.env`` in the project folder), using the
standard libpq variables PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD.
"""
import logging
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
SQL_DIR = BASE_DIR / "sql"
PACKAGE_SCHEMA = BASE_DIR / "datenbank" / "01_schema.sql"

load_dotenv(BASE_DIR / ".env")


def connect(**kwargs) -> psycopg.Connection:
    """Open a connection using the PG* environment variables."""
    return psycopg.connect("", **kwargs)


def connect_readonly(**kwargs) -> psycopg.Connection:
    """Connection for queries on behalf of agents and the chat: every transaction is READ ONLY (enforced by PostgreSQL)."""
    return psycopg.connect("", options="-c default_transaction_read_only=on", **kwargs)


def setup_logging(name: str) -> logging.Logger:
    """Log to stdout and to logs/<name>.log (progress visible with tail -f)."""
    LOG_DIR.mkdir(exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
    logger = logging.getLogger("statagent")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        for handler in (logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_DIR / f"{name}.log", encoding="utf-8")):
            handler.setFormatter(fmt)
            logger.addHandler(handler)
    return logger
