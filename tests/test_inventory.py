import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from database.db import get_db
from routes.inventario import get_availability_status


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
        category_a = _insert_category(connection, commerce_a, "Bebidas")
        category_b = _insert_category(connection, commerce_b, "Otros")

        depleted_inventory = _insert_product_inventory(
            connection,
            commerce_a,
            category_a,
            "Producto agotado",
            "A-000",
            current_stock=0,
            minimum_stock=3,
        )
        low_inventory = _insert_product_inventory(
            connection,
            commerce_a,
            category_a,
            "Producto con pocas unidades",
            "A-005",
            current_stock=5,
            minimum_stock=5,
        )
        available_inventory = _insert_product_inventory(
            connection,
            commerce_a,
            category_a,
            "Producto disponible",
            "A-008",
            current_stock=8,
            minimum_stock=5,
        )
        inactive_inventory = _insert_product_inventory(
            connection,
            commerce_a,
            category_a,
            "Producto inactivo",
            "A-I",
            current_stock=2,
            minimum_stock=1,
            active=0,
        )
        foreign_inventory = _insert_product_inventory(
            connection,
            commerce_b,
            category_b,
            "Producto secreto",
            "B-009",
            current_stock=9,
            minimum_stock=2,
        )

        connection.execute(
            """
            INSERT INTO movimiento_inventario (
                id_inventario,
                id_usuario,
                tipo,
                cantidad_delta,
                motivo,
                stock_anterior,
                stock_resultante
            ) VALUES (?, ?, 'OTRO', 2, ?, 0, 2)
            """,
            (inactive_inventory, admin_a, "Carga inicial antigua"),
        )
        connection.execute(
            """
            INSERT INTO movimiento_inventario (
                id_inventario,
                id_usuario,
                tipo,
                cantidad_delta,
                motivo,
                stock_anterior,
                stock_resultante
            ) VALUES (?, ?, 'CORRECCION', -1, ?, 3, 2)
            """,
            (inactive_inventory, admin_a, "Ajuste más reciente"),
        )
        connection.execute(
            """
            INSERT INTO movimiento_inventario (
                id_inventario,
                id_usuario,
                tipo,
                cantidad_delta,
                motivo,
                stock_anterior,
                stock_resultante
            ) VALUES (?, ?, 'REPOSICION', 9, ?, 0, 9)
            """,
            (foreign_inventory, admin_b, "Movimiento externo"),
        )
        connection.commit()

    app.config["TEST_IDS"] = {
        "commerce_a": commerce_a,
        "commerce_b": commerce_b,
        "admin_a": admin_a,
        "vendor_a": vendor_a,
        "admin_b": admin_b,
        "depleted_inventory": depleted_inventory,
        "low_inventory": low_inventory,
        "available_inventory": available_inventory,
        "inactive_inventory": inactive_inventory,
        "foreign_inventory": foreign_inventory,
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


def _insert_product_inventory(
    connection,
    commerce_id,
    category_id,
    name,
    barcode,
    current_stock,
    minimum_stock,
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
        ) VALUES (?, ?, ?, ?, 10, 15, ?)
        """,
        (commerce_id, category_id, name, barcode, active),
    ).lastrowid
    return connection.execute(
        """
        INSERT INTO inventario (
            id_producto,
            stock_actual,
            stock_minimo,
            ultima_actualizacion
        ) VALUES (?, ?, ?, '2000-01-01 00:00:00')
        """,
        (product_id, current_stock, minimum_stock),
    ).lastrowid


def _authenticate(client, user_id):
    with client.session_transaction() as user_session:
        user_session["user_id"] = user_id


def _adjust(client, inventory_id, movement_type, quantity, reason="Prueba"):
    return client.post(
        f"/inventario/{inventory_id}/ajustar",
        data={
            "tipo": movement_type,
            "cantidad": str(quantity),
            "motivo": reason,
        },
    )


def _inventory_and_movements(app, inventory_id):
    with app.app_context():
        connection = get_db()
        inventory = connection.execute(
            "SELECT * FROM inventario WHERE id_inventario = ?",
            (inventory_id,),
        ).fetchone()
        movements = connection.execute(
            """
            SELECT *
            FROM movimiento_inventario
            WHERE id_inventario = ?
            ORDER BY id_movimiento
            """,
            (inventory_id,),
        ).fetchall()
        return dict(inventory), [dict(row) for row in movements]


@pytest.mark.parametrize("user_key", ["admin_a", "vendor_a"])
def test_admin_and_vendor_can_view_inventory(app, client, user_key):
    _authenticate(client, app.config["TEST_IDS"][user_key])

    response = client.get("/inventario")

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("method", "path_template"),
    [
        ("get", "/inventario/{inventory_id}/ajustar"),
        ("post", "/inventario/{inventory_id}/stock-minimo"),
        ("get", "/inventario/movimientos"),
    ],
)
def test_vendor_cannot_use_admin_inventory_actions(
    app,
    client,
    method,
    path_template,
):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["vendor_a"])
    path = path_template.format(inventory_id=ids["available_inventory"])

    response = client.open(path, method=method.upper(), data={"stock_minimo": "2"})

    assert response.status_code == 403


def test_inventory_list_shows_exact_stock_and_isolates_commerce(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    page = client.get("/inventario").get_data(as_text=True)

    assert "Producto agotado" in page
    assert "Producto disponible" in page
    assert ">8<" in page
    assert "$15.00" in page
    assert "Producto secreto" not in page


def test_purchase_price_and_admin_controls_are_hidden_from_vendor(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    admin_page = client.get("/inventario").get_data(as_text=True)

    _authenticate(client, ids["vendor_a"])
    vendor_page = client.get("/inventario").get_data(as_text=True)

    assert "admin-purchase-price" in admin_page
    assert "Ajustar stock" in admin_page
    assert "Historial de movimientos" in admin_page
    assert "$15.00" in vendor_page
    assert "admin-purchase-price" not in vendor_page
    assert "Ajustar stock" not in vendor_page
    assert "Historial de movimientos" not in vendor_page


def test_inventory_searches_by_name_and_barcode(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    name_page = client.get("/inventario?q=agotado").get_data(as_text=True)
    code_page = client.get("/inventario?q=A-008").get_data(as_text=True)
    foreign_page = client.get("/inventario?q=B-009").get_data(as_text=True)

    assert "Producto agotado" in name_page
    assert "Producto disponible" not in name_page
    assert "Producto disponible" in code_page
    assert "Producto secreto" not in foreign_page


def test_low_stock_filter_includes_depleted_and_boundary_stock(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    page = client.get("/inventario?estado=bajo").get_data(as_text=True)

    assert "Producto agotado" in page
    assert "Producto con pocas unidades" in page
    assert "Producto disponible" not in page


@pytest.mark.parametrize(
    ("current_stock", "minimum_stock", "expected"),
    [
        (0, 0, "Agotado"),
        (0, 5, "Agotado"),
        (5, 5, "Pocas unidades"),
        (6, 5, "Disponible"),
    ],
)
def test_availability_status_is_derived(current_stock, minimum_stock, expected):
    assert get_availability_status(current_stock, minimum_stock) == expected


def test_admin_updates_minimum_stock_without_creating_movement(app, client):
    ids = app.config["TEST_IDS"]
    inventory_id = ids["available_inventory"]
    _authenticate(client, ids["admin_a"])

    response = client.post(
        f"/inventario/{inventory_id}/stock-minimo",
        data={"stock_minimo": "7"},
    )

    assert response.status_code == 302
    inventory, movements = _inventory_and_movements(app, inventory_id)
    assert inventory["stock_minimo"] == 7
    assert inventory["ultima_actualizacion"] != "2000-01-01 00:00:00"
    assert movements == []


@pytest.mark.parametrize("value", ["-1", "texto", "1.5", ""])
def test_invalid_minimum_stock_is_rejected(app, client, value):
    ids = app.config["TEST_IDS"]
    inventory_id = ids["available_inventory"]
    _authenticate(client, ids["admin_a"])

    response = client.post(
        f"/inventario/{inventory_id}/stock-minimo",
        data={"stock_minimo": value},
        follow_redirects=True,
    )

    assert "entero mayor o igual a 0" in response.get_data(as_text=True)
    inventory, movements = _inventory_and_movements(app, inventory_id)
    assert inventory["stock_minimo"] == 5
    assert movements == []


def test_minimum_stock_of_other_commerce_returns_404(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    response = client.post(
        f"/inventario/{ids['foreign_inventory']}/stock-minimo",
        data={"stock_minimo": "4"},
    )

    assert response.status_code == 404


def test_replenishment_updates_stock_and_records_traceability(app, client):
    ids = app.config["TEST_IDS"]
    inventory_id = ids["available_inventory"]
    _authenticate(client, ids["admin_a"])

    response = _adjust(
        client,
        inventory_id,
        "REPOSICION",
        3,
        reason="Ingreso de mercadería",
    )

    assert response.status_code == 302
    inventory, movements = _inventory_and_movements(app, inventory_id)
    movement = movements[-1]
    assert inventory["stock_actual"] == 11
    assert inventory["ultima_actualizacion"] != "2000-01-01 00:00:00"
    assert movement["tipo"] == "REPOSICION"
    assert movement["cantidad_delta"] == 3
    assert movement["stock_anterior"] == 8
    assert movement["stock_resultante"] == 11
    assert movement["id_usuario"] == ids["admin_a"]
    assert movement["id_venta"] is None
    assert movement["motivo"] == "Ingreso de mercadería"


def test_loss_subtracts_stock_and_records_negative_delta(app, client):
    ids = app.config["TEST_IDS"]
    inventory_id = ids["available_inventory"]
    _authenticate(client, ids["admin_a"])

    response = _adjust(client, inventory_id, "PERDIDA", 2)

    assert response.status_code == 302
    inventory, movements = _inventory_and_movements(app, inventory_id)
    assert inventory["stock_actual"] == 6
    assert movements[-1]["cantidad_delta"] == -2
    assert movements[-1]["stock_anterior"] == 8
    assert movements[-1]["stock_resultante"] == 6


@pytest.mark.parametrize(
    ("movement_type", "quantity"),
    [("PERDIDA", 9), ("CORRECCION", -9), ("OTRO", -9)],
)
def test_movements_cannot_leave_negative_stock(
    app,
    client,
    movement_type,
    quantity,
):
    ids = app.config["TEST_IDS"]
    inventory_id = ids["available_inventory"]
    _authenticate(client, ids["admin_a"])

    response = _adjust(client, inventory_id, movement_type, quantity)

    assert response.status_code == 200
    assert "dejaría el stock en negativo" in response.get_data(as_text=True)
    inventory, movements = _inventory_and_movements(app, inventory_id)
    assert inventory["stock_actual"] == 8
    assert movements == []


@pytest.mark.parametrize(
    ("quantity", "expected_stock"),
    [(3, 11), (-3, 5)],
)
def test_correction_accepts_positive_and_negative_delta(
    app,
    client,
    quantity,
    expected_stock,
):
    ids = app.config["TEST_IDS"]
    inventory_id = ids["available_inventory"]
    _authenticate(client, ids["admin_a"])

    response = _adjust(client, inventory_id, "CORRECCION", quantity)

    assert response.status_code == 302
    inventory, movements = _inventory_and_movements(app, inventory_id)
    assert inventory["stock_actual"] == expected_stock
    assert movements[-1]["cantidad_delta"] == quantity


@pytest.mark.parametrize("movement_type", ["CORRECCION", "OTRO"])
def test_delta_movement_rejects_zero(app, client, movement_type):
    ids = app.config["TEST_IDS"]
    inventory_id = ids["available_inventory"]
    _authenticate(client, ids["admin_a"])

    response = _adjust(client, inventory_id, movement_type, 0)

    assert response.status_code == 200
    assert "distinto de 0" in response.get_data(as_text=True)
    inventory, movements = _inventory_and_movements(app, inventory_id)
    assert inventory["stock_actual"] == 8
    assert movements == []


@pytest.mark.parametrize(
    ("counted_stock", "expected_delta"),
    [(12, 4), (3, -5)],
)
def test_physical_count_sets_final_stock(
    app,
    client,
    counted_stock,
    expected_delta,
):
    ids = app.config["TEST_IDS"]
    inventory_id = ids["available_inventory"]
    _authenticate(client, ids["admin_a"])

    response = _adjust(client, inventory_id, "CONTEO_FISICO", counted_stock)

    assert response.status_code == 302
    inventory, movements = _inventory_and_movements(app, inventory_id)
    assert inventory["stock_actual"] == counted_stock
    assert movements[-1]["cantidad_delta"] == expected_delta
    assert movements[-1]["stock_resultante"] == counted_stock


def test_physical_count_rejects_negative_value(app, client):
    ids = app.config["TEST_IDS"]
    inventory_id = ids["available_inventory"]
    _authenticate(client, ids["admin_a"])

    response = _adjust(client, inventory_id, "CONTEO_FISICO", -1)

    assert response.status_code == 200
    assert "stock contado debe ser mayor o igual a 0" in response.get_data(
        as_text=True
    )
    inventory, movements = _inventory_and_movements(app, inventory_id)
    assert inventory["stock_actual"] == 8
    assert movements == []


def test_unchanged_physical_count_does_not_create_movement(app, client):
    ids = app.config["TEST_IDS"]
    inventory_id = ids["available_inventory"]
    _authenticate(client, ids["admin_a"])

    response = _adjust(client, inventory_id, "CONTEO_FISICO", 8)

    assert response.status_code == 302
    with client.session_transaction() as user_session:
        messages = user_session.get("_flashes", [])
    assert any("no se registraron cambios" in message for _, message in messages)
    inventory, movements = _inventory_and_movements(app, inventory_id)
    assert inventory["stock_actual"] == 8
    assert movements == []


def test_other_movement_accepts_nonzero_delta(app, client):
    ids = app.config["TEST_IDS"]
    inventory_id = ids["available_inventory"]
    _authenticate(client, ids["admin_a"])

    response = _adjust(client, inventory_id, "OTRO", -2)

    assert response.status_code == 302
    inventory, movements = _inventory_and_movements(app, inventory_id)
    assert inventory["stock_actual"] == 6
    assert movements[-1]["tipo"] == "OTRO"
    assert movements[-1]["cantidad_delta"] == -2


@pytest.mark.parametrize("movement_type", ["VENTA", "DESCONOCIDO"])
def test_manual_adjustment_rejects_sale_and_unknown_types(
    app,
    client,
    movement_type,
):
    ids = app.config["TEST_IDS"]
    inventory_id = ids["available_inventory"]
    _authenticate(client, ids["admin_a"])

    response = _adjust(client, inventory_id, movement_type, 1)

    assert response.status_code == 200
    assert "tipo de movimiento manual válido" in response.get_data(as_text=True)
    inventory, movements = _inventory_and_movements(app, inventory_id)
    assert inventory["stock_actual"] == 8
    assert movements == []


def test_sale_is_not_an_adjustment_option(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    page = client.get(
        f"/inventario/{ids['available_inventory']}/ajustar"
    ).get_data(as_text=True)

    assert '<option value="VENTA">' not in page


@pytest.mark.parametrize("quantity", ["", "texto", "1.5"])
def test_adjustment_quantity_must_be_integer(app, client, quantity):
    ids = app.config["TEST_IDS"]
    inventory_id = ids["available_inventory"]
    _authenticate(client, ids["admin_a"])

    response = _adjust(client, inventory_id, "REPOSICION", quantity)

    assert response.status_code == 200
    assert "número entero" in response.get_data(as_text=True)
    inventory, movements = _inventory_and_movements(app, inventory_id)
    assert inventory["stock_actual"] == 8
    assert movements == []


def test_inventory_movement_rolls_back_when_history_insert_fails(app, client):
    ids = app.config["TEST_IDS"]
    inventory_id = ids["available_inventory"]
    _authenticate(client, ids["admin_a"])

    with app.app_context():
        connection = get_db()
        connection.execute(
            """
            CREATE TRIGGER fail_inventory_movement
            BEFORE INSERT ON movimiento_inventario
            BEGIN
                SELECT RAISE(ABORT, 'movement failure');
            END
            """
        )
        connection.commit()

    response = _adjust(client, inventory_id, "REPOSICION", 4)

    assert response.status_code == 200
    assert "El stock no cambió" in response.get_data(as_text=True)
    inventory, movements = _inventory_and_movements(app, inventory_id)
    assert inventory["stock_actual"] == 8
    assert movements == []


@pytest.mark.parametrize("method", ["get", "post"])
def test_adjustment_of_other_commerce_returns_404(app, client, method):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    path = f"/inventario/{ids['foreign_inventory']}/ajustar"

    if method == "get":
        response = client.get(path)
    else:
        response = client.post(
            path,
            data={"tipo": "REPOSICION", "cantidad": "1", "motivo": ""},
        )

    assert response.status_code == 404


def test_history_shows_current_commerce_traceability_in_recent_order(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    page = client.get("/inventario/movimientos").get_data(as_text=True)

    assert "Producto inactivo" in page
    assert "Ajuste más reciente" in page
    assert "Carga inicial antigua" in page
    assert page.index("Ajuste más reciente") < page.index("Carga inicial antigua")
    assert "Admin A" in page
    assert "Producto secreto" not in page
    assert "Movimiento externo" not in page


def test_history_filters_by_product_and_type(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    page = client.get(
        "/inventario/movimientos?q=inactivo&tipo=OTRO"
    ).get_data(as_text=True)

    assert "Carga inicial antigua" in page
    assert "Ajuste más reciente" not in page


def test_inactive_product_keeps_inventory_and_movements(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    inventory_page = client.get("/inventario").get_data(as_text=True)
    history_page = client.get("/inventario/movimientos").get_data(as_text=True)

    assert "Producto inactivo" in inventory_page
    assert "Inactivo" in inventory_page
    assert "Producto inactivo" in history_page
