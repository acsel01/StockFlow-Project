"""Crea una base StockFlow de demostración sin tocar la base local normal."""

import argparse
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

from werkzeug.security import generate_password_hash


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"
DEFAULT_DEMO_DATABASE = PROJECT_ROOT / "database" / "stockflow_demo.db"
DEMO_PASSWORD = "StockFlow123!"
DEMO_USERS = (
    ("Admin", "Demo", "admin@stockflow.demo", "ADMIN"),
    ("Vendedor", "Demo", "vendedor@stockflow.demo", "VENDEDOR"),
)


class DemoDatabaseExistsError(FileExistsError):
    """Evita reemplazar una base existente sin autorización explícita."""


def create_demo_database(database_path=DEFAULT_DEMO_DATABASE, reset=False):
    """Crea atómicamente una base demo; solo reemplaza con reset explícito."""
    target = Path(database_path).expanduser().resolve()
    if target.exists() and not reset:
        raise DemoDatabaseExistsError(
            f"La base demo ya existe en {target}. Usá --reset para recrearla."
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.stem}-",
        suffix=".tmp",
        dir=target.parent,
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    connection = None
    try:
        connection = sqlite3.connect(temporary_path)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        _insert_demo_data(connection)
        connection.commit()
        connection.close()
        connection = None
        os.replace(temporary_path, target)
    except Exception:
        if connection is not None:
            connection.rollback()
            connection.close()
        temporary_path.unlink(missing_ok=True)
        raise

    return target


def _insert_demo_data(connection):
    commerce_id = connection.execute(
        """
        INSERT INTO comercio (
            nombre, direccion, barrio, localidad, telefono, activo
        ) VALUES (?, ?, ?, ?, ?, 1)
        """,
        (
            "StockFlow Demo",
            "Av. Demo 123",
            "Centro",
            "Córdoba",
            "0000-000000",
        ),
    ).lastrowid

    password_hash = generate_password_hash(DEMO_PASSWORD)
    for name, surname, email, role in DEMO_USERS:
        connection.execute(
            """
            INSERT INTO usuario (
                id_comercio,
                nombre,
                apellido,
                email,
                password_hash,
                rol,
                activo
            ) VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (commerce_id, name, surname, email, password_hash, role),
        )

    beverages_id = connection.execute(
        """
        INSERT INTO categoria (id_comercio, nombre, descripcion)
        VALUES (?, 'Bebidas', 'Bebidas para la demostración')
        """,
        (commerce_id,),
    ).lastrowid
    groceries_id = connection.execute(
        """
        INSERT INTO categoria (id_comercio, nombre, descripcion)
        VALUES (?, 'Almacén', 'Productos generales para la demostración')
        """,
        (commerce_id,),
    ).lastrowid

    products = (
        {
            "category_id": beverages_id,
            "name": "Café demo",
            "description": "Producto público con precio publicado.",
            "barcode": "DEMO-001",
            "purchase_price": "40.00",
            "sale_price": "100.00",
            "visible": 1,
            "show_price": 1,
            "stock": 12,
            "minimum": 4,
        },
        {
            "category_id": groceries_id,
            "name": "Galletitas demo",
            "description": "Producto público con precio oculto.",
            "barcode": "DEMO-002",
            "purchase_price": "20.00",
            "sale_price": "55.00",
            "visible": 1,
            "show_price": 0,
            "stock": 2,
            "minimum": 3,
        },
        {
            "category_id": beverages_id,
            "name": "Agua demo agotada",
            "description": "Producto público sin existencias.",
            "barcode": "DEMO-003",
            "purchase_price": "15.00",
            "sale_price": "35.00",
            "visible": 1,
            "show_price": 1,
            "stock": 0,
            "minimum": 2,
        },
        {
            "category_id": groceries_id,
            "name": "Producto interno demo",
            "description": "Producto deliberadamente oculto del catálogo.",
            "barcode": "DEMO-004",
            "purchase_price": "30.00",
            "sale_price": "75.00",
            "visible": 0,
            "show_price": 1,
            "stock": 8,
            "minimum": 2,
        },
    )
    for product in products:
        product_id = connection.execute(
            """
            INSERT INTO producto (
                id_comercio,
                id_categoria,
                nombre,
                descripcion,
                codigo_barras,
                precio_compra,
                precio_venta,
                visible_catalogo,
                mostrar_precio_catalogo,
                activo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                commerce_id,
                product["category_id"],
                product["name"],
                product["description"],
                product["barcode"],
                product["purchase_price"],
                product["sale_price"],
                product["visible"],
                product["show_price"],
            ),
        ).lastrowid
        connection.execute(
            """
            INSERT INTO inventario (id_producto, stock_actual, stock_minimo)
            VALUES (?, ?, ?)
            """,
            (product_id, product["stock"], product["minimum"]),
        )


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Crea una base separada con datos SOLO DEMO/DESARROLLO LOCAL.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DEMO_DATABASE,
        help="Ruta de salida (default: database/stockflow_demo.db).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Recrea explícitamente la base indicada si ya existe.",
    )
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)
    try:
        database_path = create_demo_database(args.database, reset=args.reset)
    except DemoDatabaseExistsError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Base SOLO DEMO / DESARROLLO LOCAL creada correctamente:")
    print(database_path)
    print("Credenciales demo:")
    print(f"  ADMIN: admin@stockflow.demo / {DEMO_PASSWORD}")
    print(f"  VENDEDOR: vendedor@stockflow.demo / {DEMO_PASSWORD}")
    print("La demo comienza sin Caja abierta para practicar su apertura manual.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
