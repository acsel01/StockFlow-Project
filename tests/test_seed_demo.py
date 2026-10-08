import sqlite3
from contextlib import closing

import pytest
from werkzeug.security import check_password_hash

from app import create_app
from scripts.seed_demo import (
    DEMO_PASSWORD,
    DemoDatabaseExistsError,
    create_demo_database,
)


EXPECTED_TABLES = {
    "comercio",
    "usuario",
    "categoria",
    "producto",
    "inventario",
    "caja",
    "venta",
    "detalle_venta",
    "movimiento_inventario",
}


def _connect(database_path):
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def test_demo_seed_creates_complete_data_and_working_credentials(tmp_path):
    database_path = tmp_path / "stockflow_demo.db"
    assert not database_path.exists()

    assert create_demo_database(database_path) == database_path.resolve()
    assert database_path.is_file()

    with closing(_connect(database_path)) as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                """
            ).fetchall()
        }
        users = connection.execute(
            "SELECT email, password_hash, rol, activo FROM usuario ORDER BY rol"
        ).fetchall()
        products = connection.execute(
            """
            SELECT
                p.nombre,
                p.visible_catalogo,
                p.mostrar_precio_catalogo,
                i.stock_actual,
                i.stock_minimo
            FROM producto AS p
            JOIN inventario AS i ON i.id_producto = p.id_producto
            ORDER BY p.id_producto
            """
        ).fetchall()
        cash_register_count = connection.execute(
            "SELECT COUNT(*) FROM caja"
        ).fetchone()[0]

    assert tables == EXPECTED_TABLES
    assert {user["email"] for user in users} == {
        "admin@stockflow.demo",
        "vendedor@stockflow.demo",
    }
    assert {user["rol"] for user in users} == {"ADMIN", "VENDEDOR"}
    assert all(user["activo"] == 1 for user in users)
    assert all(user["password_hash"] != DEMO_PASSWORD for user in users)
    assert all(
        check_password_hash(user["password_hash"], DEMO_PASSWORD)
        for user in users
    )
    assert len(products) == 4
    assert any(
        product["visible_catalogo"] == 1
        and product["mostrar_precio_catalogo"] == 1
        for product in products
    )
    assert any(
        product["visible_catalogo"] == 1
        and product["mostrar_precio_catalogo"] == 0
        for product in products
    )
    assert any(product["visible_catalogo"] == 0 for product in products)
    assert {product["stock_actual"] for product in products} >= {0, 2, 8, 12}
    assert cash_register_count == 0

    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "demo-seed-test-secret",
        "DATABASE": str(database_path),
    })
    client = app.test_client()
    for email in ("admin@stockflow.demo", "vendedor@stockflow.demo"):
        response = client.post(
            "/login",
            data={"email": email, "password": DEMO_PASSWORD},
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/dashboard")
        client.post("/logout")


def test_demo_seed_requires_explicit_reset_and_recreates_clean_data(tmp_path):
    database_path = tmp_path / "stockflow_demo.db"
    create_demo_database(database_path)
    with closing(_connect(database_path)) as connection:
        connection.execute(
            "UPDATE comercio SET nombre = 'MARCADOR-NO-SOBREESCRIBIR'"
        )
        connection.commit()

    with pytest.raises(DemoDatabaseExistsError, match="--reset"):
        create_demo_database(database_path)

    with closing(_connect(database_path)) as connection:
        assert connection.execute(
            "SELECT nombre FROM comercio"
        ).fetchone()["nombre"] == "MARCADOR-NO-SOBREESCRIBIR"

    create_demo_database(database_path, reset=True)
    with closing(_connect(database_path)) as connection:
        assert connection.execute(
            "SELECT nombre FROM comercio"
        ).fetchone()["nombre"] == "StockFlow Demo"
        assert connection.execute("SELECT COUNT(*) FROM usuario").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM producto").fetchone()[0] == 4
