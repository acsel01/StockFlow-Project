import sqlite3

import pytest

from app import create_app
from database.db import close_db, get_db


EXPECTED_TABLES = {
    "caja",
    "categoria",
    "comercio",
    "detalle_venta",
    "inventario",
    "movimiento_inventario",
    "producto",
    "usuario",
    "venta",
}


@pytest.fixture
def app(tmp_path):
    return create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.db"),
    })


def test_init_db_creates_the_nine_expected_tables(app):
    with app.app_context():
        rows = get_db().execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            """
        ).fetchall()

    assert {row["name"] for row in rows} == EXPECTED_TABLES


def test_foreign_keys_are_enabled(app):
    with app.app_context():
        enabled = get_db().execute("PRAGMA foreign_keys").fetchone()[0]

    assert enabled == 1


def test_foreign_key_constraint_rejects_invalid_relationship(app):
    with app.app_context():
        connection = get_db()

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO usuario (
                    id_comercio, nombre, email, password_hash, rol
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (999, "Ana", "ana@example.com", "hash", "ADMIN"),
            )


def test_producto_has_independent_catalog_flags(app):
    with app.app_context():
        columns = get_db().execute("PRAGMA table_info(producto)").fetchall()

    column_names = {column["name"] for column in columns}
    assert "visible_catalogo" in column_names
    assert "mostrar_precio_catalogo" in column_names


def test_connection_reuses_sqlite_row_factory(app):
    with app.app_context():
        first_connection = get_db()
        second_connection = get_db()
        row = first_connection.execute("SELECT 7 AS cantidad").fetchone()

        assert first_connection is second_connection
        assert first_connection.row_factory is sqlite3.Row
        assert row["cantidad"] == 7


def test_close_db_is_safe_and_closes_an_open_connection(app):
    with app.app_context():
        close_db()
        connection = get_db()
        close_db()

        with pytest.raises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")
