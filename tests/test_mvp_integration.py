from copy import deepcopy
from datetime import date, datetime, time, timezone
from decimal import Decimal

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from database.db import get_db
from routes.caja import get_cash_summary
from services.estadisticas_service import (
    get_daily_sales,
    get_estimated_profit,
    get_sales_summary,
    get_top_selling_products,
)


PASSWORD = "integration-password"
PASSWORD_HASH = generate_password_hash(
    PASSWORD,
    method="pbkdf2:sha256:1000",
)


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "integration-secret-key",
        "DATABASE": str(tmp_path / "integration.db"),
    })

    with app.app_context():
        connection = get_db()
        commerce_a = _insert_commerce(connection, "Comercio Integrado A")
        commerce_b = _insert_commerce(connection, "Comercio Integrado B")
        admin_a = _insert_user(
            connection,
            commerce_a,
            "Admin A",
            "admin-a@integration.test",
            "ADMIN",
        )
        vendor_a = _insert_user(
            connection,
            commerce_a,
            "Vendedor A",
            "vendor-a@integration.test",
            "VENDEDOR",
        )
        admin_b = _insert_user(
            connection,
            commerce_b,
            "Admin B",
            "admin-b@integration.test",
            "ADMIN",
        )
        category_a = _insert_category(connection, commerce_a, "Almacén A")
        category_b = _insert_category(connection, commerce_b, "Almacén B")
        product_a, inventory_a = _insert_product(
            connection,
            commerce_a,
            category_a,
            "Café integrado A",
            "INTEGRATION-A-1",
            "40.00",
            "100.00",
            stock=3,
            minimum_stock=2,
            visible=1,
            show_price=1,
        )
        hidden_price_product, hidden_price_inventory = _insert_product(
            connection,
            commerce_a,
            category_a,
            "Té sin precio público",
            "INTEGRATION-A-2",
            "10.00",
            "876543.21",
            stock=6,
            minimum_stock=1,
            visible=1,
            show_price=0,
        )
        product_b, inventory_b = _insert_product(
            connection,
            commerce_b,
            category_b,
            "Producto exclusivo B",
            "INTEGRATION-B-1",
            "100.00",
            "250.00",
            stock=9,
            minimum_stock=1,
            visible=1,
            show_price=1,
        )
        cash_b = _insert_cash_register(connection, commerce_b, admin_b, "70.00")
        connection.commit()

    app.config["TEST_IDS"] = {
        "commerce_a": commerce_a,
        "commerce_b": commerce_b,
        "admin_a": admin_a,
        "vendor_a": vendor_a,
        "admin_b": admin_b,
        "category_a": category_a,
        "category_b": category_b,
        "product_a": product_a,
        "inventory_a": inventory_a,
        "hidden_price_product": hidden_price_product,
        "hidden_price_inventory": hidden_price_inventory,
        "product_b": product_b,
        "inventory_b": inventory_b,
        "cash_b": cash_b,
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


def _insert_user(connection, commerce_id, name, email, role):
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
    minimum_stock,
    visible,
    show_price,
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
            visible_catalogo,
            mostrar_precio_catalogo,
            activo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            commerce_id,
            category_id,
            name,
            barcode,
            purchase_price,
            sale_price,
            visible,
            show_price,
        ),
    ).lastrowid
    inventory_id = connection.execute(
        """
        INSERT INTO inventario (id_producto, stock_actual, stock_minimo)
        VALUES (?, ?, ?)
        """,
        (product_id, stock, minimum_stock),
    ).lastrowid
    return product_id, inventory_id


def _insert_cash_register(connection, commerce_id, user_id, initial_amount):
    return connection.execute(
        """
        INSERT INTO caja (
            id_comercio, id_usuario_apertura, monto_inicial, estado
        ) VALUES (?, ?, ?, 'ABIERTA')
        """,
        (commerce_id, user_id, initial_amount),
    ).lastrowid


def _login(client, email):
    response = client.post(
        "/login",
        data={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def _logout(client):
    response = client.post("/logout")
    assert response.status_code == 302


def _add_to_cart(client, product_id, quantity):
    response = client.post(
        f"/punto-venta/agregar/{product_id}",
        data={"cantidad": str(quantity)},
    )
    assert response.status_code == 302


def _cart(client):
    with client.session_transaction() as user_session:
        return deepcopy(user_session.get("pos_cart", {}))


def _product_card(page, product_name):
    name_index = page.index(product_name)
    start = page.rfind("<article", 0, name_index)
    end = page.index("</article>", name_index) + len("</article>")
    return page[start:end]


def _commerce_snapshot(app, commerce_id):
    with app.app_context():
        connection = get_db()
        return {
            "stock": [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT p.id_producto, i.stock_actual, i.stock_minimo
                    FROM producto AS p
                    JOIN inventario AS i ON i.id_producto = p.id_producto
                    WHERE p.id_comercio = ?
                    ORDER BY p.id_producto
                    """,
                    (commerce_id,),
                ).fetchall()
            ],
            "cash": [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT id_caja, monto_inicial, efectivo_contado, estado
                    FROM caja
                    WHERE id_comercio = ?
                    ORDER BY id_caja
                    """,
                    (commerce_id,),
                ).fetchall()
            ],
            "sales": connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM venta AS v
                JOIN caja AS c ON c.id_caja = v.id_caja
                WHERE c.id_comercio = ?
                """,
                (commerce_id,),
            ).fetchone()["total"],
        }


def test_complete_mvp_flow_connects_public_catalog_pos_and_reporting(app, client):
    ids = app.config["TEST_IDS"]
    commerce_b_before = _commerce_snapshot(app, ids["commerce_b"])

    catalog_before = client.get(
        f"/catalogo/{ids['commerce_a']}"
    ).get_data(as_text=True)
    assert "$ 100.00" in _product_card(catalog_before, "Café integrado A")
    assert "Disponible" in _product_card(catalog_before, "Café integrado A")
    assert "Té sin precio público" in catalog_before
    assert "Precio no publicado" in catalog_before
    assert "876543.21" not in catalog_before

    _login(client, "vendor-a@integration.test")
    open_response = client.post("/caja/abrir", data={"monto_inicial": "100.00"})
    assert open_response.status_code == 302
    _add_to_cart(client, ids["product_a"], 1)
    sale_response = client.post(
        "/punto-venta/confirmar",
        data={
            "medio_pago": "EFECTIVO",
            "dinero_recibido": "150.00",
            "observaciones": "Flujo integral del MVP",
        },
    )
    assert sale_response.status_code == 302
    assert _cart(client) == {}

    with app.app_context():
        connection = get_db()
        cash_a = connection.execute(
            "SELECT * FROM caja WHERE id_comercio = ?",
            (ids["commerce_a"],),
        ).fetchone()
        sale = connection.execute("SELECT * FROM venta").fetchone()
        detail = connection.execute("SELECT * FROM detalle_venta").fetchone()
        movement = connection.execute(
            "SELECT * FROM movimiento_inventario"
        ).fetchone()
        inventory = connection.execute(
            "SELECT * FROM inventario WHERE id_inventario = ?",
            (ids["inventory_a"],),
        ).fetchone()
        cash_summary = get_cash_summary(connection, cash_a["id_caja"], cash_a)
        all_time_summary = get_sales_summary(
            connection,
            ids["commerce_a"],
        )
        today_summary = get_sales_summary(
            connection,
            ids["commerce_a"],
            date.today(),
            date.today(),
        )
        top_products = get_top_selling_products(
            connection,
            ids["commerce_a"],
        )
        estimated_profit = get_estimated_profit(
            connection,
            ids["commerce_a"],
        )

        assert sale["id_caja"] == cash_a["id_caja"]
        assert sale["id_usuario"] == ids["vendor_a"]
        assert sale["medio_pago"] == "EFECTIVO"
        assert Decimal(str(sale["total"])) == Decimal("100")
        assert Decimal(str(sale["dinero_recibido"])) == Decimal("150")
        assert Decimal(str(sale["vuelto"])) == Decimal("50")
        assert detail["id_venta"] == sale["id_venta"]
        assert detail["id_producto"] == ids["product_a"]
        assert detail["cantidad"] == 1
        assert movement["id_venta"] == sale["id_venta"]
        assert movement["tipo"] == "VENTA"
        assert movement["cantidad_delta"] == -1
        assert movement["stock_anterior"] == 3
        assert movement["stock_resultante"] == 2
        assert inventory["stock_actual"] == 2
        assert cash_summary["cantidad_ventas"] == 1
        assert cash_summary["total_vendido"] == Decimal("100")
        assert cash_summary["total_efectivo"] == Decimal("100")
        assert cash_summary["efectivo_esperado"] == Decimal("200")
        assert all_time_summary == {
            "total_sold": Decimal("100.00"),
            "sale_count": 1,
            "average_ticket": Decimal("100.00"),
            "units_sold": 1,
        }
        assert today_summary == all_time_summary
        assert top_products[0]["product_name"] == "Café integrado A"
        assert top_products[0]["units_sold"] == 1
        assert estimated_profit == Decimal("60.00")

    sale_id = sale["id_venta"]
    assert sale_response.headers["Location"].endswith(f"/ventas/{sale_id}")
    detail_page = client.get(f"/ventas/{sale_id}").get_data(as_text=True)
    history_page = client.get("/ventas").get_data(as_text=True)
    cash_page = client.get("/caja").get_data(as_text=True)
    vendor_dashboard = client.get("/dashboard").get_data(as_text=True)
    assert "Café integrado A" in detail_page
    assert "EFECTIVO" in history_page
    assert "$ 100.00" in history_page
    assert "Ventas completadas" in cash_page
    assert "$ 200.00" in cash_page
    assert "Ventas de la caja actual" in vendor_dashboard
    assert "$ 100.00" in vendor_dashboard

    catalog_after = client.get(
        f"/catalogo/{ids['commerce_a']}"
    ).get_data(as_text=True)
    assert "Pocas unidades" in _product_card(catalog_after, "Café integrado A")
    assert "$ 100.00" in _product_card(catalog_after, "Café integrado A")

    _logout(client)
    _login(client, "admin-a@integration.test")
    admin_dashboard = client.get("/dashboard").get_data(as_text=True)
    statistics = client.get("/estadisticas?periodo=todo").get_data(as_text=True)
    assert "Total vendido hoy" in admin_dashboard
    assert "$ 100.00" in admin_dashboard
    assert "Café integrado A" in statistics
    assert "$ 60.00" in statistics

    close_response = client.post(
        "/caja/cerrar",
        data={"efectivo_contado": "200.00"},
    )
    assert close_response.status_code == 302
    with app.app_context():
        connection = get_db()
        closed_cash = connection.execute(
            "SELECT * FROM caja WHERE id_comercio = ?",
            (ids["commerce_a"],),
        ).fetchone()
        closed_summary = get_cash_summary(
            connection,
            closed_cash["id_caja"],
            closed_cash,
        )
        assert closed_cash["estado"] == "CERRADA"
        assert closed_cash["id_usuario_cierre"] == ids["admin_a"]
        assert Decimal(str(closed_cash["efectivo_contado"])) == Decimal("200")
        assert closed_summary["diferencia"] == Decimal("0")

    _logout(client)
    _login(client, "admin-b@integration.test")
    dashboard_b = client.get("/dashboard").get_data(as_text=True)
    statistics_b = client.get("/estadisticas?periodo=todo").get_data(as_text=True)
    catalog_b = client.get(
        f"/catalogo/{ids['commerce_b']}"
    ).get_data(as_text=True)
    assert "Café integrado A" not in dashboard_b
    assert "Café integrado A" not in statistics_b
    assert "Café integrado A" not in catalog_b
    assert "Producto exclusivo B" in catalog_b
    assert _commerce_snapshot(app, ids["commerce_b"]) == commerce_b_before


def test_checkout_without_open_cash_register_keeps_everything_unchanged(
    app,
    client,
):
    ids = app.config["TEST_IDS"]
    _login(client, "vendor-a@integration.test")
    _add_to_cart(client, ids["product_a"], 1)

    response = client.post(
        "/punto-venta/confirmar",
        data={"medio_pago": "EFECTIVO", "dinero_recibido": "100.00"},
        follow_redirects=True,
    )

    assert "No hay una caja abierta" in response.get_data(as_text=True)
    assert _cart(client) == {str(ids["product_a"]): 1}
    with app.app_context():
        connection = get_db()
        assert connection.execute("SELECT COUNT(*) FROM venta").fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM detalle_venta"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM movimiento_inventario"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT stock_actual FROM inventario WHERE id_inventario = ?",
            (ids["inventory_a"],),
        ).fetchone()[0] == 3


def test_stock_change_before_checkout_rejects_every_partial_sale(app, client):
    ids = app.config["TEST_IDS"]
    _login(client, "vendor-a@integration.test")
    client.post("/caja/abrir", data={"monto_inicial": "0"})
    _add_to_cart(client, ids["product_a"], 2)
    with app.app_context():
        connection = get_db()
        connection.execute(
            "UPDATE inventario SET stock_actual = 1 WHERE id_inventario = ?",
            (ids["inventory_a"],),
        )
        connection.commit()

    response = client.post(
        "/punto-venta/confirmar",
        data={"medio_pago": "EFECTIVO", "dinero_recibido": "200.00"},
        follow_redirects=True,
    )

    assert "Stock insuficiente" in response.get_data(as_text=True)
    assert _cart(client) == {str(ids["product_a"]): 2}
    with app.app_context():
        connection = get_db()
        assert connection.execute("SELECT COUNT(*) FROM venta").fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM detalle_venta"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM movimiento_inventario"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT stock_actual FROM inventario WHERE id_inventario = ?",
            (ids["inventory_a"],),
        ).fetchone()[0] == 1


def test_representative_access_matrix_for_anonymous_vendor_and_admin(app, client):
    ids = app.config["TEST_IDS"]
    assert client.get("/catalogo").status_code == 200
    assert client.get(f"/catalogo/{ids['commerce_a']}").status_code == 200

    internal_routes = (
        "/dashboard",
        "/productos",
        "/categorias",
        "/inventario",
        "/inventario/movimientos",
        "/punto-venta",
        "/ventas",
        "/caja",
        "/estadisticas",
    )
    for path in internal_routes:
        response = client.get(path)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")

    _login(client, "vendor-a@integration.test")
    for path in (
        "/dashboard",
        "/inventario",
        "/punto-venta",
        "/ventas",
        "/caja",
    ):
        assert client.get(path).status_code == 200
    for path in (
        "/productos",
        "/categorias",
        "/inventario/movimientos",
        "/estadisticas",
    ):
        assert client.get(path).status_code == 403

    _logout(client)
    _login(client, "admin-a@integration.test")
    for path in internal_routes:
        assert client.get(path).status_code == 200


def test_application_starts_from_missing_database_with_full_schema(tmp_path):
    database_path = tmp_path / "fresh" / "stockflow.db"
    assert not database_path.exists()

    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "clean-database-secret",
        "DATABASE": str(database_path),
    })

    assert database_path.is_file()
    with app.app_context():
        connection = get_db()
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
        assert tables == {
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
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json() == {
        "application": "StockFlow",
        "status": "ok",
    }


def test_utc_sale_timestamp_is_classified_by_local_calendar_date(app):
    ids = app.config["TEST_IDS"]
    local_now = datetime.now().astimezone()
    local_timezone = local_now.tzinfo
    local_offset = local_now.utcoffset()
    offset_seconds = local_offset.total_seconds() if local_offset is not None else 0
    if offset_seconds < 0:
        controlled_time = time(23, 59)
    elif offset_seconds > 0:
        controlled_time = time(0, 1)
    else:
        controlled_time = time(0, 30)
    local_datetime = datetime.combine(
        local_now.date(),
        controlled_time,
        tzinfo=local_timezone,
    )
    utc_datetime = local_datetime.astimezone(timezone.utc)
    utc_timestamp = utc_datetime.strftime("%Y-%m-%d %H:%M:%S")
    local_day = local_datetime.date()
    if offset_seconds:
        assert utc_datetime.date() != local_day

    with app.app_context():
        connection = get_db()
        cash_register_id = _insert_cash_register(
            connection,
            ids["commerce_a"],
            ids["admin_a"],
            "0.00",
        )
        sale_id = connection.execute(
            """
            INSERT INTO venta (
                id_caja,
                id_usuario,
                fecha_hora,
                subtotal,
                descuento,
                total,
                medio_pago,
                estado
            ) VALUES (?, ?, ?, 123.45, 0, 123.45, 'DEBITO', 'COMPLETADA')
            """,
            (cash_register_id, ids["vendor_a"], utc_timestamp),
        ).lastrowid
        connection.execute(
            """
            INSERT INTO detalle_venta (
                id_venta,
                id_producto,
                cantidad,
                precio_unitario,
                subtotal
            ) VALUES (?, ?, 1, 123.45, 123.45)
            """,
            (sale_id, ids["product_a"]),
        )
        connection.commit()

        summary = get_sales_summary(
            connection,
            ids["commerce_a"],
            local_day,
            local_day,
        )
        daily_sales = get_daily_sales(
            connection,
            ids["commerce_a"],
            local_day,
            local_day,
        )

    assert summary == {
        "total_sold": Decimal("123.45"),
        "sale_count": 1,
        "average_ticket": Decimal("123.45"),
        "units_sold": 1,
    }
    assert daily_sales == [{
        "sale_date": local_day.isoformat(),
        "sale_count": 1,
        "total_sold": Decimal("123.45"),
    }]
