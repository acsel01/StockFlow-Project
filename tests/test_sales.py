import sqlite3
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from database.db import get_db
from services.venta_service import VentaError, confirmar_venta


PASSWORD_HASH = generate_password_hash(
    "test-password",
    method="pbkdf2:sha256:1000",
)


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "DATABASE": str(tmp_path / "test.db"),
    })

    with app.app_context():
        connection = get_db()
        commerce_a = _insert_commerce(connection, "Comercio A")
        commerce_b = _insert_commerce(connection, "Comercio B")
        admin_a = _insert_user(connection, commerce_a, "Admin A", "ADMIN")
        vendor_a = _insert_user(connection, commerce_a, "Vendedor A", "VENDEDOR")
        inactive_a = _insert_user(
            connection,
            commerce_a,
            "Usuario Inactivo",
            "VENDEDOR",
            active=0,
        )
        admin_b = _insert_user(connection, commerce_b, "Admin B", "ADMIN")
        category_a = _insert_category(connection, commerce_a, "Almacén")
        category_b = _insert_category(connection, commerce_b, "Otros")
        product_a, inventory_a = _insert_product(
            connection,
            commerce_a,
            category_a,
            "Producto A",
            "A-100",
            purchase_price="13.37",
            sale_price="100.00",
            stock=10,
        )
        product_a2, inventory_a2 = _insert_product(
            connection,
            commerce_a,
            category_a,
            "Producto B",
            "A-255",
            purchase_price="8.00",
            sale_price="25.50",
            stock=5,
        )
        inactive_product, inactive_inventory = _insert_product(
            connection,
            commerce_a,
            category_a,
            "Producto inactivo",
            "A-OFF",
            purchase_price="5.00",
            sale_price="40.00",
            stock=3,
            active=0,
        )
        foreign_product, foreign_inventory = _insert_product(
            connection,
            commerce_b,
            category_b,
            "Producto externo",
            "B-100",
            purchase_price="10.00",
            sale_price="75.00",
            stock=7,
        )
        open_cash_a = _insert_cash_register(
            connection,
            commerce_a,
            admin_a,
            "ABIERTA",
        )
        closed_cash_a = _insert_cash_register(
            connection,
            commerce_a,
            admin_a,
            "CERRADA",
        )
        open_cash_b = _insert_cash_register(
            connection,
            commerce_b,
            admin_b,
            "ABIERTA",
        )
        connection.commit()

    app.config["TEST_IDS"] = {
        "commerce_a": commerce_a,
        "commerce_b": commerce_b,
        "admin_a": admin_a,
        "vendor_a": vendor_a,
        "inactive_a": inactive_a,
        "admin_b": admin_b,
        "product_a": product_a,
        "product_a2": product_a2,
        "inactive_product": inactive_product,
        "foreign_product": foreign_product,
        "inventory_a": inventory_a,
        "inventory_a2": inventory_a2,
        "inactive_inventory": inactive_inventory,
        "foreign_inventory": foreign_inventory,
        "open_cash_a": open_cash_a,
        "closed_cash_a": closed_cash_a,
        "open_cash_b": open_cash_b,
    }
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _insert_commerce(connection, name):
    return connection.execute(
        "INSERT INTO comercio (nombre, direccion) VALUES (?, ?)",
        (name, f"Dirección de {name}"),
    ).lastrowid


def _insert_user(connection, commerce_id, name, role, active=1):
    email = name.lower().replace(" ", "-") + "@example.com"
    return connection.execute(
        """
        INSERT INTO usuario (
            id_comercio, nombre, email, password_hash, rol, activo
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (commerce_id, name, email, PASSWORD_HASH, role, active),
    ).lastrowid


def _insert_category(connection, commerce_id, name):
    return connection.execute(
        "INSERT INTO categoria (id_comercio, nombre) VALUES (?, ?)",
        (commerce_id, name),
    ).lastrowid


def _insert_product(
    connection,
    commerce_id,
    category_id,
    name,
    barcode,
    purchase_price,
    sale_price,
    stock,
    active=1,
):
    product_id = connection.execute(
        """
        INSERT INTO producto (
            id_comercio,
            id_categoria,
            nombre,
            codigo_barras,
            precio_compra,
            precio_venta,
            activo
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            commerce_id,
            category_id,
            name,
            barcode,
            purchase_price,
            sale_price,
            active,
        ),
    ).lastrowid
    inventory_id = connection.execute(
        """
        INSERT INTO inventario (
            id_producto,
            stock_actual,
            stock_minimo,
            ultima_actualizacion
        ) VALUES (?, ?, 0, '2000-01-01 00:00:00')
        """,
        (product_id, stock),
    ).lastrowid
    return product_id, inventory_id


def _insert_cash_register(connection, commerce_id, user_id, status):
    closed_values = (
        ", id_usuario_cierre, fecha_cierre, efectivo_contado"
        if status == "CERRADA"
        else ""
    )
    closed_placeholders = ", ?, CURRENT_TIMESTAMP, 0" if status == "CERRADA" else ""
    parameters = [commerce_id, user_id, status]
    if status == "CERRADA":
        parameters.append(user_id)
    return connection.execute(
        f"""
        INSERT INTO caja (
            id_comercio, id_usuario_apertura, monto_inicial, estado{closed_values}
        ) VALUES (?, ?, 0, ?{closed_placeholders})
        """,
        parameters,
    ).lastrowid


def _authenticate(client, user_id):
    with client.session_transaction() as user_session:
        user_session["user_id"] = user_id


def _confirm(app, **overrides):
    ids = app.config["TEST_IDS"]
    arguments = {
        "caja_id": ids["open_cash_a"],
        "usuario_id": ids["admin_a"],
        "items": [{"id_producto": ids["product_a"], "cantidad": 1}],
        "medio_pago": "EFECTIVO",
        "dinero_recibido": "100.00",
    }
    arguments.update(overrides)
    with app.app_context():
        return confirmar_venta(get_db(), **arguments)


def _table_rows(app, table):
    with app.app_context():
        return [
            dict(row)
            for row in get_db().execute(
                f"SELECT * FROM {table} ORDER BY 1"
            ).fetchall()
        ]


def _stock(app, inventory_id):
    with app.app_context():
        return dict(get_db().execute(
            "SELECT * FROM inventario WHERE id_inventario = ?",
            (inventory_id,),
        ).fetchone())


def test_simple_cash_sale_creates_full_traceability(app):
    ids = app.config["TEST_IDS"]

    result = _confirm(app, dinero_recibido="150")

    sales = _table_rows(app, "venta")
    details = _table_rows(app, "detalle_venta")
    movements = _table_rows(app, "movimiento_inventario")
    inventory = _stock(app, ids["inventory_a"])
    assert result["id_venta"] == sales[0]["id_venta"]
    assert result["subtotal"] == Decimal("100.00")
    assert result["descuento"] == Decimal("0.00")
    assert result["total"] == Decimal("100.00")
    assert result["vuelto"] == Decimal("50.00")
    assert sales[0]["id_caja"] == ids["open_cash_a"]
    assert sales[0]["id_usuario"] == ids["admin_a"]
    assert sales[0]["subtotal"] == 100
    assert sales[0]["descuento"] == 0
    assert sales[0]["total"] == 100
    assert sales[0]["dinero_recibido"] == 150
    assert sales[0]["vuelto"] == 50
    assert sales[0]["estado"] == "COMPLETADA"
    assert details[0]["id_producto"] == ids["product_a"]
    assert details[0]["cantidad"] == 1
    assert details[0]["precio_unitario"] == 100
    assert details[0]["subtotal"] == 100
    assert inventory["stock_actual"] == 9
    assert inventory["ultima_actualizacion"] != "2000-01-01 00:00:00"
    assert movements[0]["tipo"] == "VENTA"
    assert movements[0]["cantidad_delta"] == -1
    assert movements[0]["stock_anterior"] == 10
    assert movements[0]["stock_resultante"] == 9
    assert movements[0]["id_usuario"] == ids["admin_a"]
    assert movements[0]["id_venta"] == sales[0]["id_venta"]
    assert movements[0]["motivo"] == f"Venta #{sales[0]['id_venta']}"


def test_sale_with_multiple_products_calculates_backend_totals(app):
    ids = app.config["TEST_IDS"]

    result = _confirm(
        app,
        items=[
            {"id_producto": ids["product_a"], "cantidad": 2, "precio": 1},
            {"id_producto": ids["product_a2"], "cantidad": 3, "precio": 1},
        ],
        medio_pago="TRANSFERENCIA",
        dinero_recibido="9999",
        observaciones="Venta combinada",
    )

    assert result["total"] == Decimal("276.50")
    assert result["dinero_recibido"] is None
    assert result["vuelto"] is None
    sale = _table_rows(app, "venta")[0]
    details = _table_rows(app, "detalle_venta")
    assert sale["subtotal"] == 276.5
    assert sale["total"] == 276.5
    assert sale["observaciones"] == "Venta combinada"
    assert len(details) == 2
    assert details[0]["precio_unitario"] == 100
    assert details[0]["subtotal"] == 200
    assert details[1]["precio_unitario"] == 25.5
    assert details[1]["subtotal"] == 76.5
    assert _stock(app, ids["inventory_a"])["stock_actual"] == 8
    assert _stock(app, ids["inventory_a2"])["stock_actual"] == 2


def test_duplicate_items_are_combined_before_stock_validation(app):
    ids = app.config["TEST_IDS"]

    _confirm(
        app,
        items=[
            {"id_producto": ids["product_a"], "cantidad": 2},
            {"id_producto": ids["product_a"], "cantidad": 3},
        ],
        dinero_recibido="500",
    )

    details = _table_rows(app, "detalle_venta")
    assert len(details) == 1
    assert details[0]["cantidad"] == 5
    assert details[0]["subtotal"] == 500
    assert _stock(app, ids["inventory_a"])["stock_actual"] == 5


def test_empty_cart_is_rejected(app):
    with pytest.raises(VentaError, match="al menos un producto"):
        _confirm(app, items=[])

    assert _table_rows(app, "venta") == []


@pytest.mark.parametrize("quantity", [0, -1, 1.5, "1.5", "texto", None, True])
def test_invalid_quantities_are_rejected(app, quantity):
    ids = app.config["TEST_IDS"]

    with pytest.raises(VentaError, match="entero mayor a cero"):
        _confirm(
            app,
            items=[{"id_producto": ids["product_a"], "cantidad": quantity}],
        )

    assert _table_rows(app, "venta") == []
    assert _stock(app, ids["inventory_a"])["stock_actual"] == 10


def test_string_integer_ids_and_quantities_are_accepted(app):
    ids = app.config["TEST_IDS"]

    _confirm(
        app,
        items=[{"id_producto": str(ids["product_a"]), "cantidad": "2"}],
        dinero_recibido="200",
    )

    assert _table_rows(app, "detalle_venta")[0]["cantidad"] == 2


@pytest.mark.parametrize(
    ("item_overrides", "message"),
    [
        ({"id_producto": 999999, "cantidad": 1}, "no existe"),
        ({"id_producto": None, "cantidad": 1}, "no es válido"),
    ],
)
def test_missing_or_invalid_product_is_rejected(app, item_overrides, message):
    with pytest.raises(VentaError, match=message):
        _confirm(app, items=[item_overrides])

    assert _table_rows(app, "venta") == []


def test_product_from_other_commerce_is_rejected(app):
    ids = app.config["TEST_IDS"]

    with pytest.raises(VentaError, match="no pertenece"):
        _confirm(
            app,
            items=[{"id_producto": ids["foreign_product"], "cantidad": 1}],
        )

    assert _table_rows(app, "venta") == []
    assert _stock(app, ids["inventory_a"])["stock_actual"] == 10
    assert _stock(app, ids["foreign_inventory"])["stock_actual"] == 7


def test_product_deactivated_before_confirmation_is_rejected(app):
    ids = app.config["TEST_IDS"]

    with pytest.raises(VentaError, match="está inactivo"):
        _confirm(
            app,
            items=[{"id_producto": ids["inactive_product"], "cantidad": 1}],
        )

    assert _table_rows(app, "venta") == []
    assert _stock(app, ids["inactive_inventory"])["stock_actual"] == 3


def test_insufficient_stock_rejects_whole_sale(app):
    ids = app.config["TEST_IDS"]

    with pytest.raises(VentaError, match="Stock insuficiente"):
        _confirm(
            app,
            items=[
                {"id_producto": ids["product_a"], "cantidad": 1},
                {"id_producto": ids["product_a2"], "cantidad": 6},
            ],
        )

    assert _table_rows(app, "venta") == []
    assert _stock(app, ids["inventory_a"])["stock_actual"] == 10
    assert _stock(app, ids["inventory_a2"])["stock_actual"] == 5


@pytest.mark.parametrize(
    ("cash_key", "user_key"),
    [
        (None, "admin_a"),
        ("closed_cash_a", "admin_a"),
        ("open_cash_b", "admin_a"),
    ],
)
def test_invalid_closed_or_foreign_cash_register_is_rejected(
    app,
    cash_key,
    user_key,
):
    ids = app.config["TEST_IDS"]
    cash_id = 999999 if cash_key is None else ids[cash_key]

    with pytest.raises(VentaError, match="caja abierta válida"):
        _confirm(app, caja_id=cash_id, usuario_id=ids[user_key])

    assert _table_rows(app, "venta") == []


def test_cash_register_closed_before_confirmation_is_revalidated(app):
    ids = app.config["TEST_IDS"]
    with app.app_context():
        connection = get_db()
        connection.execute(
            "UPDATE caja SET estado = 'CERRADA' WHERE id_caja = ?",
            (ids["open_cash_a"],),
        )
        connection.commit()

    with pytest.raises(VentaError, match="caja abierta válida"):
        _confirm(app)

    assert _table_rows(app, "venta") == []
    assert _stock(app, ids["inventory_a"])["stock_actual"] == 10


@pytest.mark.parametrize("user_key", [None, "inactive_a"])
def test_missing_or_inactive_user_is_rejected(app, user_key):
    ids = app.config["TEST_IDS"]
    user_id = 999999 if user_key is None else ids[user_key]

    with pytest.raises(VentaError, match="no está habilitado"):
        _confirm(app, usuario_id=user_id)

    assert _table_rows(app, "venta") == []


def test_user_must_belong_to_cash_register_commerce(app):
    ids = app.config["TEST_IDS"]

    with pytest.raises(VentaError, match="caja abierta válida"):
        _confirm(app, usuario_id=ids["admin_b"])

    assert _table_rows(app, "venta") == []


def test_current_database_price_is_used_at_confirmation(app):
    ids = app.config["TEST_IDS"]
    conceptual_cart = [{
        "id_producto": ids["product_a"],
        "cantidad": 2,
        "precio_unitario": "1.00",
        "subtotal": "2.00",
    }]
    with app.app_context():
        connection = get_db()
        connection.execute(
            "UPDATE producto SET precio_venta = 150 WHERE id_producto = ?",
            (ids["product_a"],),
        )
        connection.commit()

    result = _confirm(
        app,
        items=conceptual_cart,
        dinero_recibido="300",
    )

    detail = _table_rows(app, "detalle_venta")[0]
    assert result["total"] == Decimal("300.00")
    assert detail["precio_unitario"] == 150
    assert detail["subtotal"] == 300


@pytest.mark.parametrize(
    "received",
    [None, "texto", "NaN", "Infinity", "99.99"],
)
def test_invalid_or_insufficient_cash_is_rejected(app, received):
    with pytest.raises(VentaError, match="efectivo recibido"):
        _confirm(app, dinero_recibido=received)

    assert _table_rows(app, "venta") == []


@pytest.mark.parametrize("payment_method", ["DEBITO", "CREDITO", "TRANSFERENCIA"])
def test_non_cash_payments_ignore_received_values(app, payment_method):
    result = _confirm(
        app,
        medio_pago=payment_method,
        dinero_recibido="999999",
    )

    sale = _table_rows(app, "venta")[0]
    assert result["dinero_recibido"] is None
    assert result["vuelto"] is None
    assert sale["dinero_recibido"] is None
    assert sale["vuelto"] is None


def test_unknown_payment_method_is_rejected(app):
    with pytest.raises(VentaError, match="medio de pago"):
        _confirm(app, medio_pago="CRIPTOMONEDA")

    assert _table_rows(app, "venta") == []


def test_deep_database_failure_rolls_back_every_sale_change(app):
    ids = app.config["TEST_IDS"]
    with app.app_context():
        connection = get_db()
        connection.execute(
            """
            CREATE TRIGGER fail_sale_movement
            BEFORE INSERT ON movimiento_inventario
            BEGIN
                SELECT RAISE(ABORT, 'movement failure');
            END
            """
        )
        connection.commit()

    with pytest.raises(VentaError, match="No se registraron cambios"):
        _confirm(app)

    assert _table_rows(app, "venta") == []
    assert _table_rows(app, "detalle_venta") == []
    assert _table_rows(app, "movimiento_inventario") == []
    assert _stock(app, ids["inventory_a"])["stock_actual"] == 10
    assert _stock(app, ids["inventory_a"])["ultima_actualizacion"] == (
        "2000-01-01 00:00:00"
    )


def test_concurrent_sales_cannot_oversell_stock(app):
    ids = app.config["TEST_IDS"]
    database_path = app.config["DATABASE"]
    with app.app_context():
        connection = get_db()
        connection.execute(
            "UPDATE inventario SET stock_actual = 5 WHERE id_inventario = ?",
            (ids["inventory_a"],),
        )
        connection.commit()
    barrier = Barrier(2)

    def attempt_sale():
        connection = sqlite3.connect(database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        barrier.wait()
        try:
            result = confirmar_venta(
                connection,
                ids["open_cash_a"],
                ids["admin_a"],
                [{"id_producto": ids["product_a"], "cantidad": 4}],
                "EFECTIVO",
                "400",
            )
            return "success", result["id_venta"]
        except VentaError as error:
            return "error", str(error)
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: attempt_sale(), range(2)))

    assert sorted(status for status, _ in results) == ["error", "success"]
    assert "Stock insuficiente" in next(
        message for status, message in results if status == "error"
    )
    assert len(_table_rows(app, "venta")) == 1
    assert len(_table_rows(app, "detalle_venta")) == 1
    assert len(_table_rows(app, "movimiento_inventario")) == 1
    assert _stock(app, ids["inventory_a"])["stock_actual"] == 1


@pytest.mark.parametrize("user_key", ["admin_a", "vendor_a"])
def test_admin_and_vendor_can_view_sales_history(app, client, user_key):
    ids = app.config["TEST_IDS"]
    _confirm(app)
    _authenticate(client, ids[user_key])

    response = client.get("/ventas")

    assert response.status_code == 200
    assert "Historial de ventas" in response.get_data(as_text=True)
    assert "Producto A" not in response.get_data(as_text=True)


@pytest.mark.parametrize("path", ["/ventas", "/ventas/1"])
def test_sales_history_and_detail_require_login(client, path):
    response = client.get(path)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_history_is_recent_first_and_filters_payment_method(app, client):
    ids = app.config["TEST_IDS"]
    first = _confirm(app, medio_pago="DEBITO")
    second = _confirm(app, medio_pago="CREDITO")
    _authenticate(client, ids["admin_a"])

    page = client.get("/ventas").get_data(as_text=True)
    debit_page = client.get("/ventas?medio_pago=DEBITO").get_data(as_text=True)

    assert page.index(f"#{second['id_venta']}") < page.index(f"#{first['id_venta']}")
    assert f"#{first['id_venta']}" in debit_page
    assert f"#{second['id_venta']}" not in debit_page


def test_history_and_detail_are_isolated_by_commerce(app, client):
    ids = app.config["TEST_IDS"]
    own_sale = _confirm(app)
    foreign_sale = _confirm(
        app,
        caja_id=ids["open_cash_b"],
        usuario_id=ids["admin_b"],
        items=[{"id_producto": ids["foreign_product"], "cantidad": 1}],
        dinero_recibido="75",
    )
    _authenticate(client, ids["admin_a"])

    history = client.get("/ventas").get_data(as_text=True)
    foreign_detail = client.get(f"/ventas/{foreign_sale['id_venta']}")

    assert f"#{own_sale['id_venta']}" in history
    assert f"#{foreign_sale['id_venta']}" not in history
    assert "Producto externo" not in history
    assert foreign_detail.status_code == 404


def test_detail_uses_historical_price_after_product_price_changes(app, client):
    ids = app.config["TEST_IDS"]
    result = _confirm(app, observaciones="Cliente habitual")
    with app.app_context():
        connection = get_db()
        connection.execute(
            "UPDATE producto SET precio_venta = 150 WHERE id_producto = ?",
            (ids["product_a"],),
        )
        connection.commit()
    _authenticate(client, ids["vendor_a"])

    page = client.get(f"/ventas/{result['id_venta']}").get_data(as_text=True)

    assert "Producto A" in page
    assert "A-100" in page
    assert "Cliente habitual" in page
    assert "Precio unitario histórico" in page
    assert "$ 100.00" in page
    assert "$ 150.00" not in page


def test_vendor_never_sees_costs_margins_or_profit(app, client):
    ids = app.config["TEST_IDS"]
    result = _confirm(app)
    _authenticate(client, ids["vendor_a"])

    history = client.get("/ventas").get_data(as_text=True).lower()
    detail = client.get(f"/ventas/{result['id_venta']}").get_data(as_text=True).lower()

    for page in (history, detail):
        assert "13.37" not in page
        assert "precio de compra" not in page
        assert "margen" not in page
        assert "ganancia" not in page


def test_point_of_sale_remains_a_placeholder(app, client):
    _authenticate(client, app.config["TEST_IDS"]["admin_a"])

    page = client.get("/punto-venta").get_data(as_text=True)

    assert "Módulo preparado para comenzar su implementación" in page
    assert "carrito" not in page.lower()
