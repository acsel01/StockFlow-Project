from copy import deepcopy

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from database.db import get_db


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
        admin_b = _insert_user(connection, commerce_b, "Admin B", "ADMIN")
        category_a = _insert_category(connection, commerce_a, "Almacén")
        category_b = _insert_category(connection, commerce_b, "Otros")
        product_a, inventory_a = _insert_product(
            connection,
            commerce_a,
            category_a,
            "Yerba tradicional",
            "7790001",
            "13.37",
            "100.00",
            5,
        )
        product_a2, inventory_a2 = _insert_product(
            connection,
            commerce_a,
            category_a,
            "Galletitas",
            "7790002",
            "8.00",
            "25.50",
            4,
        )
        inactive_product, inactive_inventory = _insert_product(
            connection,
            commerce_a,
            category_a,
            "Producto inactivo",
            "7790999",
            "4.00",
            "40.00",
            3,
            active=0,
        )
        foreign_product, foreign_inventory = _insert_product(
            connection,
            commerce_b,
            category_b,
            "Producto externo",
            "8800001",
            "20.00",
            "75.00",
            8,
        )
        open_cash_a = _insert_cash_register(connection, commerce_a, admin_a)
        open_cash_b = _insert_cash_register(connection, commerce_b, admin_b)
        connection.commit()

    app.config["TEST_IDS"] = {
        "commerce_a": commerce_a,
        "commerce_b": commerce_b,
        "admin_a": admin_a,
        "vendor_a": vendor_a,
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


def _insert_user(connection, commerce_id, name, role):
    email = name.lower().replace(" ", "-") + "@example.com"
    return connection.execute(
        """
        INSERT INTO usuario (
            id_comercio, nombre, email, password_hash, rol
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (commerce_id, name, email, PASSWORD_HASH, role),
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
        INSERT INTO inventario (id_producto, stock_actual, stock_minimo)
        VALUES (?, ?, 0)
        """,
        (product_id, stock),
    ).lastrowid
    return product_id, inventory_id


def _insert_cash_register(connection, commerce_id, user_id):
    return connection.execute(
        """
        INSERT INTO caja (
            id_comercio, id_usuario_apertura, monto_inicial, estado
        ) VALUES (?, ?, 100, 'ABIERTA')
        """,
        (commerce_id, user_id),
    ).lastrowid


def _authenticate(client, user_id):
    with client.session_transaction() as user_session:
        user_session["user_id"] = user_id


def _add(client, product_id, quantity=1, follow_redirects=False):
    return client.post(
        f"/punto-venta/agregar/{product_id}",
        data={"cantidad": str(quantity)},
        follow_redirects=follow_redirects,
    )


def _cart(client):
    with client.session_transaction() as user_session:
        return deepcopy(user_session.get("pos_cart", {}))


def _rows(app, table):
    with app.app_context():
        return [
            dict(row)
            for row in get_db().execute(
                f"SELECT * FROM {table} ORDER BY 1"
            ).fetchall()
        ]


def _stock(app, inventory_id):
    with app.app_context():
        return get_db().execute(
            "SELECT stock_actual FROM inventario WHERE id_inventario = ?",
            (inventory_id,),
        ).fetchone()["stock_actual"]


def test_anonymous_user_is_redirected_to_login(client):
    response = client.get("/punto-venta")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


@pytest.mark.parametrize("user_key", ["admin_a", "vendor_a"])
def test_admin_and_vendor_can_access_pos(app, client, user_key):
    _authenticate(client, app.config["TEST_IDS"][user_key])

    response = client.get("/punto-venta")

    assert response.status_code == 200
    assert "Punto de venta" in response.get_data(as_text=True)


def test_product_search_by_name_and_barcode_is_scoped_and_operational(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["vendor_a"])

    name_page = client.get("/punto-venta?q=yerba").get_data(as_text=True)
    code_page = client.get("/punto-venta?q=7790002").get_data(as_text=True)
    all_page = client.get("/punto-venta").get_data(as_text=True)

    assert "Yerba tradicional" in name_page
    assert "Galletitas" not in name_page
    assert "Galletitas" in code_page
    assert "Yerba tradicional" not in code_page
    assert "Producto externo" not in all_page
    assert "Producto inactivo" not in all_page
    assert "13.37" not in all_page
    assert "$ 100.00" in all_page
    assert ">5<" in all_page


def test_adding_product_stores_only_id_and_quantity_without_reserving_stock(
    app,
    client,
):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    response = _add(client, ids["product_a"], 2)

    assert response.status_code == 302
    assert _cart(client) == {str(ids["product_a"]): 2}
    assert _stock(app, ids["inventory_a"]) == 5
    serialized_cart = str(_cart(client)).lower()
    for forbidden in ("precio", "subtotal", "total", "stock", "comercio", "caja"):
        assert forbidden not in serialized_cart


def test_adding_same_product_increments_existing_quantity(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    _add(client, ids["product_a"], 1)
    _add(client, ids["product_a"], 2)

    assert _cart(client) == {str(ids["product_a"]): 3}


def test_quantity_can_be_updated_and_product_removed(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    _add(client, ids["product_a"])

    update = client.post(
        f"/punto-venta/{ids['product_a']}/cantidad",
        data={"cantidad": "4"},
    )
    assert update.status_code == 302
    assert _cart(client) == {str(ids["product_a"]): 4}

    remove = client.post(f"/punto-venta/{ids['product_a']}/quitar")
    assert remove.status_code == 302
    assert _cart(client) == {}


def test_removing_missing_product_is_idempotent(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    response = client.post(f"/punto-venta/{ids['product_a']}/quitar")

    assert response.status_code == 302
    assert _cart(client) == {}


@pytest.mark.parametrize("quantity", ["0", "-1", "1.5", "texto", ""])
def test_invalid_add_quantity_is_rejected(app, client, quantity):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    response = _add(client, ids["product_a"], quantity, follow_redirects=True)

    assert "entero mayor a cero" in response.get_data(as_text=True)
    assert _cart(client) == {}


@pytest.mark.parametrize("quantity", ["0", "-1", "1.5", "texto", ""])
def test_invalid_updated_quantity_preserves_cart(app, client, quantity):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    _add(client, ids["product_a"], 2)

    response = client.post(
        f"/punto-venta/{ids['product_a']}/cantidad",
        data={"cantidad": quantity},
        follow_redirects=True,
    )

    assert "entero mayor a cero" in response.get_data(as_text=True)
    assert _cart(client) == {str(ids["product_a"]): 2}


def test_cart_cannot_exceed_current_stock(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    _add(client, ids["product_a"], 4)

    add_response = _add(client, ids["product_a"], 2, follow_redirects=True)
    update_response = client.post(
        f"/punto-venta/{ids['product_a']}/cantidad",
        data={"cantidad": "6"},
        follow_redirects=True,
    )

    assert "Stock insuficiente" in add_response.get_data(as_text=True)
    assert "Stock insuficiente" in update_response.get_data(as_text=True)
    assert _cart(client) == {str(ids["product_a"]): 4}


@pytest.mark.parametrize("product_key", ["foreign_product", "inactive_product"])
def test_foreign_or_inactive_product_cannot_be_added(app, client, product_key):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    response = _add(client, ids[product_key], follow_redirects=True)

    assert "no está disponible para este comercio" in response.get_data(as_text=True)
    assert _cart(client) == {}


def test_logout_clears_cart_and_identity(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["vendor_a"])
    _add(client, ids["product_a"])

    client.post("/logout")

    with client.session_transaction() as user_session:
        assert "user_id" not in user_session
        assert "pos_cart" not in user_session


def test_cart_subtotals_and_total_are_recalculated_in_backend(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    _add(client, ids["product_a"], 2)
    _add(client, ids["product_a2"], 1)

    page = client.get("/punto-venta").get_data(as_text=True)

    assert "$ 200.00" in page
    assert "$ 25.50" in page
    assert "$ 225.50" in page


def test_price_change_after_add_is_reflected_on_reload(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    _add(client, ids["product_a"], 2)
    with app.app_context():
        connection = get_db()
        connection.execute(
            "UPDATE producto SET precio_venta = 150 WHERE id_producto = ?",
            (ids["product_a"],),
        )
        connection.commit()

    page = client.get("/punto-venta").get_data(as_text=True)

    assert "$ 150.00" in page
    assert "$ 300.00" in page
    assert _cart(client) == {str(ids["product_a"]): 2}


def test_open_cash_register_is_shown(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    page = client.get("/punto-venta").get_data(as_text=True)

    assert f"Caja #{ids['open_cash_a']} abierta" in page


def test_without_open_cash_register_checkout_is_rejected_and_cart_remains(
    app,
    client,
):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    _add(client, ids["product_a"])
    with app.app_context():
        connection = get_db()
        connection.execute(
            "UPDATE caja SET estado = 'CERRADA' WHERE id_caja = ?",
            (ids["open_cash_a"],),
        )
        connection.commit()

    page = client.get("/punto-venta").get_data(as_text=True)
    response = client.post(
        "/punto-venta/confirmar",
        data={"medio_pago": "EFECTIVO", "dinero_recibido": "100"},
        follow_redirects=True,
    )

    assert "No hay una caja abierta" in page
    assert "No hay una caja abierta" in response.get_data(as_text=True)
    assert _cart(client) == {str(ids["product_a"]): 1}
    assert _rows(app, "venta") == []


def test_empty_cart_cannot_be_confirmed(app, client):
    _authenticate(client, app.config["TEST_IDS"]["admin_a"])

    response = client.post(
        "/punto-venta/confirmar",
        data={"medio_pago": "EFECTIVO", "dinero_recibido": "100"},
        follow_redirects=True,
    )

    assert "El carrito está vacío" in response.get_data(as_text=True)
    assert _rows(app, "venta") == []


def test_vendor_end_to_end_cash_checkout_uses_sales_service(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["vendor_a"])
    _add(client, ids["product_a"])
    client.post(
        f"/punto-venta/{ids['product_a']}/cantidad",
        data={"cantidad": "2"},
    )

    response = client.post(
        "/punto-venta/confirmar",
        data={
            "medio_pago": "EFECTIVO",
            "dinero_recibido": "250",
            "observaciones": "Venta desde POS",
            "total": "1",
            "precio": "1",
            "stock": "9999",
        },
    )

    assert response.status_code == 302
    sale = _rows(app, "venta")[0]
    detail = _rows(app, "detalle_venta")[0]
    movement = _rows(app, "movimiento_inventario")[0]
    assert response.headers["Location"].endswith(f"/ventas/{sale['id_venta']}")
    assert sale["id_caja"] == ids["open_cash_a"]
    assert sale["id_usuario"] == ids["vendor_a"]
    assert sale["total"] == 200
    assert sale["dinero_recibido"] == 250
    assert sale["vuelto"] == 50
    assert sale["observaciones"] == "Venta desde POS"
    assert detail["id_producto"] == ids["product_a"]
    assert detail["cantidad"] == 2
    assert detail["precio_unitario"] == 100
    assert _stock(app, ids["inventory_a"]) == 3
    assert movement["id_venta"] == sale["id_venta"]
    assert movement["id_usuario"] == ids["vendor_a"]
    assert movement["cantidad_delta"] == -2
    assert _cart(client) == {}


def test_success_flash_reports_sale_total_and_change(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    _add(client, ids["product_a"])

    response = client.post(
        "/punto-venta/confirmar",
        data={"medio_pago": "EFECTIVO", "dinero_recibido": "150"},
        follow_redirects=True,
    )
    page = response.get_data(as_text=True)

    assert "confirmada correctamente" in page
    assert "Total: $100.00" in page
    assert "Vuelto: $50.00" in page


def test_service_error_keeps_cart_and_database_consistent(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    _add(client, ids["product_a"], 2)

    response = client.post(
        "/punto-venta/confirmar",
        data={"medio_pago": "EFECTIVO", "dinero_recibido": "50"},
        follow_redirects=True,
    )

    assert "efectivo recibido es insuficiente" in response.get_data(as_text=True)
    assert _cart(client) == {str(ids["product_a"]): 2}
    assert _rows(app, "venta") == []
    assert _rows(app, "detalle_venta") == []
    assert _rows(app, "movimiento_inventario") == []
    assert _stock(app, ids["inventory_a"]) == 5


def test_stock_change_before_checkout_prevents_overselling_and_keeps_cart(
    app,
    client,
):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    _add(client, ids["product_a"], 4)
    with app.app_context():
        connection = get_db()
        connection.execute(
            "UPDATE inventario SET stock_actual = 2 WHERE id_inventario = ?",
            (ids["inventory_a"],),
        )
        connection.commit()

    page = client.get("/punto-venta").get_data(as_text=True)
    response = client.post(
        "/punto-venta/confirmar",
        data={"medio_pago": "EFECTIVO", "dinero_recibido": "400"},
        follow_redirects=True,
    )

    assert "cantidad supera el stock actual" in page
    assert "Stock insuficiente" in response.get_data(as_text=True)
    assert _cart(client) == {str(ids["product_a"]): 4}
    assert _rows(app, "venta") == []
    assert _stock(app, ids["inventory_a"]) == 2


def test_price_change_is_used_by_checkout_and_saved_as_historical_price(
    app,
    client,
):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    _add(client, ids["product_a"])
    with app.app_context():
        connection = get_db()
        connection.execute(
            "UPDATE producto SET precio_venta = 150 WHERE id_producto = ?",
            (ids["product_a"],),
        )
        connection.commit()

    client.post(
        "/punto-venta/confirmar",
        data={"medio_pago": "EFECTIVO", "dinero_recibido": "150"},
    )

    assert _rows(app, "venta")[0]["total"] == 150
    assert _rows(app, "detalle_venta")[0]["precio_unitario"] == 150


@pytest.mark.parametrize("payment_method", ["DEBITO", "CREDITO", "TRANSFERENCIA"])
def test_non_cash_checkout_is_delegated_to_service(app, client, payment_method):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    _add(client, ids["product_a"])

    client.post(
        "/punto-venta/confirmar",
        data={"medio_pago": payment_method, "dinero_recibido": "9999"},
    )

    sale = _rows(app, "venta")[0]
    assert sale["medio_pago"] == payment_method
    assert sale["dinero_recibido"] is None
    assert sale["vuelto"] is None
    assert _cart(client) == {}


def test_cancel_cart_is_repeatable_and_never_changes_database(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    _add(client, ids["product_a"], 2)
    cash_before = _rows(app, "caja")
    inventory_before = _stock(app, ids["inventory_a"])

    first = client.post("/punto-venta/cancelar")
    second = client.post("/punto-venta/cancelar")

    assert first.status_code == 302
    assert second.status_code == 302
    assert _cart(client) == {}
    assert _rows(app, "venta") == []
    assert _rows(app, "detalle_venta") == []
    assert _rows(app, "movimiento_inventario") == []
    assert _stock(app, ids["inventory_a"]) == inventory_before
    assert _rows(app, "caja") == cash_before
