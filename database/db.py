import sqlite3
from pathlib import Path

from flask import current_app, g


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def get_db() -> sqlite3.Connection:
    """Obtiene la conexión SQLite de la solicitud actual."""
    if "db" not in g:
        database_path = Path(current_app.config["DATABASE"])
        database_path.parent.mkdir(parents=True, exist_ok=True)

        g.db = sqlite3.connect(database_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")

    return g.db


def close_db(error=None) -> None:
    """Cierra la conexión SQLite si fue abierta en este contexto."""
    connection = g.pop("db", None)

    if connection is not None:
        connection.close()


def init_db() -> None:
    """Crea las tablas definidas en database/schema.sql."""
    connection = get_db()
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
