from datetime import datetime, timezone

import pytest

from app import create_app
from database.db import get_db
from utils.datetime_utils import format_local_datetime


UTC_TIMESTAMP = "2026-10-08 15:30:19"


def _expected_local_datetime(value=UTC_TIMESTAMP):
    return (
        datetime.fromisoformat(value)
        .replace(tzinfo=timezone.utc)
        .astimezone()
        .strftime("%d/%m/%Y %H:%M")
    )


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "datetime-display-test-key",
            "DATABASE": str(
                tmp_path_factory.mktemp("datetime-display") / "test.db"
            ),
        }
    )

    with app.app_context():
        connection = get_db()
        commerce_id = connection.execute(
            "INSERT INTO comercio (nombre, direccion) VALUES (?, ?)",
            ("Comercio horario", "Calle UTC 123"),
        ).lastrowid
        user_id = connection.execute(
            """
            INSERT INTO usuario (
                id_comercio, nombre, email, password_hash, rol
            ) VALUES (?, ?, ?, ?, 'ADMIN')
            """,
            (commerce_id, "Admin horario", "time@example.com", "unused"),
        ).lastrowid
        category_id = connection.execute(
            "INSERT INTO categoria (id_comercio, nombre) VALUES (?, ?)",
            (commerce_id, "Horario"),
        ).lastrowid
        product_id = connection.execute(
            """
            INSERT INTO producto (
                id_comercio, id_categoria, nombre, codigo_barras,
                precio_compra, precio_venta, activo
            ) VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (commerce_id, category_id, "Producto horario", "UTC-001", 10, 20),
        ).lastrowid
        inventory_id = connection.execute(
            """
            INSERT INTO inventario (
                id_producto, stock_actual, stock_minimo, ultima_actualizacion
            ) VALUES (?, 10, 2, ?)
            """,
            (product_id, UTC_TIMESTAMP),
        ).lastrowid
        cash_register_id = connection.execute(
            """
            INSERT INTO caja (
                id_comercio, id_usuario_apertura, fecha_apertura,
                monto_inicial, estado
            ) VALUES (?, ?, ?, 100, 'ABIERTA')
            """,
            (commerce_id, user_id, UTC_TIMESTAMP),
        ).lastrowid
        sale_id = connection.execute(
            """
            INSERT INTO venta (
                id_caja, id_usuario, fecha_hora, subtotal, descuento,
                total, medio_pago, estado
            ) VALUES (?, ?, ?, 20, 0, 20, 'DEBITO', 'COMPLETADA')
            """,
            (cash_register_id, user_id, UTC_TIMESTAMP),
        ).lastrowid
        connection.execute(
            """
            INSERT INTO movimiento_inventario (
                id_inventario, id_usuario, tipo, cantidad_delta, motivo,
                stock_anterior, stock_resultante, fecha_hora
            ) VALUES (?, ?, 'REPOSICION', 1, 'Prueba horaria', 9, 10, ?)
            """,
            (inventory_id, user_id, UTC_TIMESTAMP),
        )
        connection.commit()

    app.config["DATETIME_DISPLAY_IDS"] = {
        "user": user_id,
        "product": product_id,
        "sale": sale_id,
    }
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _authenticate(client, user_id):
    with client.session_transaction() as user_session:
        user_session["user_id"] = user_id


def test_sqlite_utc_timestamp_is_formatted_in_system_timezone():
    assert format_local_datetime(UTC_TIMESTAMP) == _expected_local_datetime()


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, ""), ("", ""), ("valor inválido", "valor inválido")],
)
def test_local_datetime_uses_safe_display_fallbacks(value, expected):
    assert format_local_datetime(value) == expected


def test_local_datetime_accepts_naive_and_aware_datetime_values():
    naive_value = datetime(2026, 10, 8, 15, 30, 19)
    aware_value = naive_value.replace(tzinfo=timezone.utc)
    expected = _expected_local_datetime()

    assert format_local_datetime(naive_value) == expected
    assert format_local_datetime(aware_value) == expected


def test_visible_internal_timestamps_use_local_datetime_filter(app, client):
    ids = app.config["DATETIME_DISPLAY_IDS"]
    _authenticate(client, ids["user"])
    expected = _expected_local_datetime()
    paths = (
        "/dashboard",
        "/caja",
        "/ventas",
        f"/ventas/{ids['sale']}",
        "/inventario/movimientos",
    )

    for path in paths:
        response = client.get(path)
        page = response.get_data(as_text=True)

        assert response.status_code == 200
        assert expected in page
        assert UTC_TIMESTAMP not in page


def test_numeric_inventory_and_pos_inputs_keep_readable_width_classes(
    app,
    client,
):
    ids = app.config["DATETIME_DISPLAY_IDS"]
    _authenticate(client, ids["user"])

    inventory_page = client.get("/inventario").get_data(as_text=True)
    assert "sf-stock-minimum-input" in inventory_page

    client.post(
        f"/punto-venta/agregar/{ids['product']}",
        data={"cantidad": "1"},
    )
    pos_page = client.get("/punto-venta").get_data(as_text=True)
    assert pos_page.count("sf-quantity-input") >= 2
