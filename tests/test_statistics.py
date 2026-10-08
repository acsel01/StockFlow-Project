import html
import json
import re
from datetime import date, timedelta
from decimal import Decimal

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from database.db import get_db
from services.estadisticas_service import (
    get_daily_sales,
    get_estimated_profit,
    get_low_stock_products,
    get_sales_summary,
    get_top_profitable_products,
    get_top_selling_products,
    resolve_period,
)


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
    today = date.today()

    with app.app_context():
        connection = get_db()
        commerce_a = _insert_commerce(connection, "Comercio A")
        commerce_b = _insert_commerce(connection, "Comercio B")
        commerce_empty = _insert_commerce(connection, "Comercio sin ventas")
        admin_a = _insert_user(connection, commerce_a, "Admin A", "ADMIN")
        vendor_a = _insert_user(connection, commerce_a, "Vendedor A", "VENDEDOR")
        admin_b = _insert_user(connection, commerce_b, "Admin B", "ADMIN")
        admin_empty = _insert_user(
            connection,
            commerce_empty,
            "Admin Vacío",
            "ADMIN",
        )
        category_a = _insert_category(connection, commerce_a, "Almacén")
        category_b = _insert_category(connection, commerce_b, "Otros")

        yerba, yerba_inventory = _insert_product(
            connection,
            commerce_a,
            category_a,
            "Yerba histórica",
            "A-100",
            purchase_price=60,
            sale_price=150,
            stock=10,
            minimum_stock=2,
        )
        cookies, cookies_inventory = _insert_product(
            connection,
            commerce_a,
            category_a,
            "Galletitas",
            "A-020",
            purchase_price=10,
            sale_price=20,
            stock=8,
            minimum_stock=2,
        )
        depleted, depleted_inventory = _insert_product(
            connection,
            commerce_a,
            category_a,
            "Producto agotado",
            "A-000",
            purchase_price=5,
            sale_price=15,
            stock=0,
            minimum_stock=3,
        )
        low, low_inventory = _insert_product(
            connection,
            commerce_a,
            category_a,
            "Producto con pocas unidades",
            "A-003",
            purchase_price=5,
            sale_price=15,
            stock=3,
            minimum_stock=3,
        )
        inactive_low, inactive_inventory = _insert_product(
            connection,
            commerce_a,
            category_a,
            "Inactivo con stock bajo",
            "A-OFF",
            purchase_price=5,
            sale_price=15,
            stock=0,
            minimum_stock=5,
            active=0,
        )
        foreign_product, foreign_inventory = _insert_product(
            connection,
            commerce_b,
            category_b,
            "Stock secreto B",
            "B-000",
            purchase_price=1,
            sale_price=999,
            stock=0,
            minimum_stock=5,
        )
        cash_a = _insert_cash_register(connection, commerce_a, admin_a)
        cash_b = _insert_cash_register(connection, commerce_b, admin_b)
        cash_empty = _insert_cash_register(connection, commerce_empty, admin_empty)

        sale_specs = [
            (0, yerba, 2, 100, 200),
            (0, cookies, 1, 20, 20),
            (-6, yerba, 1, 100, 100),
            (-7, cookies, 1, 20, 20),
            (-29, yerba, 1, 100, 100),
            (-30, cookies, 1, 20, 20),
        ]
        sale_ids = []
        for offset, product_id, quantity, unit_price, total in sale_specs:
            sale_ids.append(_insert_sale(
                connection,
                cash_a,
                vendor_a,
                today + timedelta(days=offset),
                product_id,
                quantity,
                unit_price,
                total,
            ))
        foreign_sale = _insert_sale(
            connection,
            cash_b,
            admin_b,
            today,
            foreign_product,
            3,
            999,
            2997,
        )
        connection.commit()

    app.config["TEST_IDS"] = {
        "commerce_a": commerce_a,
        "commerce_b": commerce_b,
        "commerce_empty": commerce_empty,
        "admin_a": admin_a,
        "vendor_a": vendor_a,
        "admin_b": admin_b,
        "admin_empty": admin_empty,
        "yerba": yerba,
        "cookies": cookies,
        "depleted": depleted,
        "low": low,
        "inactive_low": inactive_low,
        "foreign_product": foreign_product,
        "yerba_inventory": yerba_inventory,
        "cookies_inventory": cookies_inventory,
        "depleted_inventory": depleted_inventory,
        "low_inventory": low_inventory,
        "inactive_inventory": inactive_inventory,
        "foreign_inventory": foreign_inventory,
        "cash_a": cash_a,
        "cash_b": cash_b,
        "cash_empty": cash_empty,
        "sale_ids": sale_ids,
        "foreign_sale": foreign_sale,
        "today": today,
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
        VALUES (?, ?, ?)
        """,
        (product_id, stock, minimum_stock),
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


def _insert_sale(
    connection,
    cash_id,
    user_id,
    sale_date,
    product_id,
    quantity,
    unit_price,
    total,
):
    timestamp = f"{sale_date.isoformat()} 12:00:00"
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
        ) VALUES (?, ?, ?, ?, 0, ?, 'DEBITO', 'COMPLETADA')
        """,
        (cash_id, user_id, timestamp, total, total),
    ).lastrowid
    connection.execute(
        """
        INSERT INTO detalle_venta (
            id_venta, id_producto, cantidad, precio_unitario, subtotal
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (sale_id, product_id, quantity, unit_price, unit_price * quantity),
    )
    return sale_id


def _authenticate(client, user_id):
    with client.session_transaction() as user_session:
        user_session["user_id"] = user_id


def _chart_data(page):
    match = re.search(
        r'<script id="statistics-chart-data" type="application/json">(.*?)</script>',
        page,
        re.DOTALL,
    )
    assert match is not None
    return json.loads(html.unescape(match.group(1)))


def _database_snapshot(app):
    tables = (
        "venta",
        "detalle_venta",
        "producto",
        "inventario",
        "caja",
        "movimiento_inventario",
    )
    with app.app_context():
        connection = get_db()
        return {
            table: [
                dict(row)
                for row in connection.execute(
                    f"SELECT * FROM {table} ORDER BY 1"
                ).fetchall()
            ]
            for table in tables
        }


@pytest.mark.parametrize("path", ["/dashboard", "/estadisticas"])
def test_internal_analytics_require_login(client, path):
    response = client.get(path)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


@pytest.mark.parametrize("user_key", ["admin_a", "vendor_a"])
def test_admin_and_vendor_can_access_dashboard(app, client, user_key):
    _authenticate(client, app.config["TEST_IDS"][user_key])

    response = client.get("/dashboard")

    assert response.status_code == 200


def test_statistics_remains_admin_only(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    assert client.get("/estadisticas").status_code == 200

    _authenticate(client, ids["vendor_a"])
    assert client.get("/estadisticas").status_code == 403


def test_admin_dashboard_shows_today_summary_cash_and_low_stock(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    page = client.get("/dashboard").get_data(as_text=True)

    assert "$ 220.00" in page
    assert "Ventas de hoy" in page
    assert ">2<" in page
    assert "$ 110.00" in page
    assert f"Caja #{ids['cash_a']} abierta" in page
    assert "Producto agotado" in page
    assert "Producto con pocas unidades" in page
    assert "Stock secreto B" not in page
    assert "Ver estadísticas" in page


def test_vendor_dashboard_is_operational_and_hides_owner_metrics(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["vendor_a"])

    page = client.get("/dashboard").get_data(as_text=True)
    lower_page = page.lower()

    assert "Ventas de la caja actual" in page
    assert ">6<" in page
    assert "$ 460.00" in page
    assert "Producto agotado" in page
    assert "Punto de Venta" in page
    assert "Inventario" in page
    assert "Ventas" in page
    for sensitive in (
        "precio de compra",
        "costo",
        "margen",
        "ganancia",
        "rentabilidad",
        "ver estadísticas",
    ):
        assert sensitive not in lower_page
    assert 'href="/estadisticas"' not in page


def test_default_statistics_uses_last_30_inclusive_days(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    page = client.get("/estadisticas").get_data(as_text=True)

    assert "Últimos 30 días" in page
    assert "$ 440.00" in page
    assert "Cantidad de ventas" in page
    assert ">5<" in page
    assert "$ 88.00" in page
    assert "Unidades vendidas" in page
    assert ">6<" in page
    assert "$ 180.00" in page


def test_statistics_rankings_use_historical_details(app):
    ids = app.config["TEST_IDS"]
    with app.app_context():
        connection = get_db()
        period = resolve_period("30d", today=ids["today"])
        products = get_top_selling_products(
            connection,
            ids["commerce_a"],
            period["date_from"],
            period["date_to"],
        )

    assert products[0]["product_name"] == "Yerba histórica"
    assert products[0]["units_sold"] == 4
    assert products[0]["total_sold"] == Decimal("400.00")


def test_price_change_does_not_rewrite_historical_revenue(app):
    ids = app.config["TEST_IDS"]
    with app.app_context():
        connection = get_db()
        connection.execute(
            "UPDATE producto SET precio_venta = 999 WHERE id_producto = ?",
            (ids["yerba"],),
        )
        connection.commit()
        summary = get_sales_summary(connection, ids["commerce_a"])
        ranking = get_top_selling_products(connection, ids["commerce_a"])

    assert summary["total_sold"] == Decimal("460.00")
    assert ranking[0]["total_sold"] == Decimal("400.00")


def test_inactive_product_remains_in_historical_rankings(app):
    ids = app.config["TEST_IDS"]
    with app.app_context():
        connection = get_db()
        connection.execute(
            "UPDATE producto SET activo = 0 WHERE id_producto = ?",
            (ids["yerba"],),
        )
        connection.commit()
        ranking = get_top_selling_products(connection, ids["commerce_a"])

    assert ranking[0]["product_name"] == "Yerba histórica"
    assert ranking[0]["units_sold"] == 4


def test_estimated_profit_uses_current_purchase_cost(app):
    ids = app.config["TEST_IDS"]
    with app.app_context():
        connection = get_db()
        initial_profit = get_estimated_profit(connection, ids["commerce_a"])
        connection.execute(
            "UPDATE producto SET precio_compra = 70 WHERE id_producto = ?",
            (ids["yerba"],),
        )
        connection.commit()
        changed_profit = get_estimated_profit(connection, ids["commerce_a"])
        ranking = get_top_profitable_products(connection, ids["commerce_a"])

    assert initial_profit == Decimal("190.00")
    assert changed_profit == Decimal("150.00")
    assert ranking[0]["product_name"] == "Yerba histórica"
    assert ranking[0]["estimated_profit"] == Decimal("120.00")


def test_estimated_profit_limitation_is_visible(app, client):
    _authenticate(client, app.config["TEST_IDS"]["admin_a"])

    page = client.get("/estadisticas").get_data(as_text=True)

    assert "Ganancia bruta estimada" in page
    assert "estimada utilizando el costo de compra actual" in page


def test_daily_sales_and_chart_data_match_aggregations(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    page = client.get("/estadisticas").get_data(as_text=True)
    chart_data = _chart_data(page)

    with app.app_context():
        period = resolve_period("30d", today=ids["today"])
        daily = get_daily_sales(
            get_db(),
            ids["commerce_a"],
            period["date_from"],
            period["date_to"],
        )

    assert chart_data["daily_sales"]["labels"] == [
        row["sale_date"] for row in daily
    ]
    assert chart_data["daily_sales"]["values"] == [
        str(row["total_sold"]) for row in daily
    ]
    assert chart_data["top_products"]["labels"][0] == "Yerba histórica"
    assert chart_data["top_products"]["values"][0] == 4


def test_low_stock_is_current_active_and_independent_of_period(app, client):
    ids = app.config["TEST_IDS"]
    with app.app_context():
        products = get_low_stock_products(get_db(), ids["commerce_a"])

    assert [product["product_name"] for product in products] == [
        "Producto agotado",
        "Producto con pocas unidades",
    ]
    _authenticate(client, ids["admin_a"])
    page = client.get("/estadisticas?periodo=hoy").get_data(as_text=True)
    assert "Stock bajo actual" in page
    assert "no depende del período de ventas" in page


@pytest.mark.parametrize(
    ("period_key", "start_offset", "end_offset"),
    [
        ("hoy", 0, 0),
        ("7d", -6, 0),
        ("30d", -29, 0),
    ],
)
def test_standard_period_boundaries(period_key, start_offset, end_offset, app):
    today = app.config["TEST_IDS"]["today"]

    period = resolve_period(period_key, today=today)

    assert period["date_from"] == today + timedelta(days=start_offset)
    assert period["date_to"] == today + timedelta(days=end_offset)


def test_month_and_all_period_boundaries(app):
    today = app.config["TEST_IDS"]["today"]

    month = resolve_period("mes", today=today)
    all_time = resolve_period("todo", today=today)

    assert month["date_from"] == today.replace(day=1)
    assert month["date_to"] == today
    assert all_time["date_from"] is None
    assert all_time["date_to"] is None


@pytest.mark.parametrize(
    ("period_key", "expected_total", "expected_count"),
    [
        ("hoy", "$ 220.00", 2),
        ("7d", "$ 320.00", 3),
        ("30d", "$ 440.00", 5),
        ("todo", "$ 460.00", 6),
    ],
)
def test_statistics_period_routes(
    app,
    client,
    period_key,
    expected_total,
    expected_count,
):
    _authenticate(client, app.config["TEST_IDS"]["admin_a"])

    page = client.get(
        f"/estadisticas?periodo={period_key}"
    ).get_data(as_text=True)

    assert expected_total in page
    assert f">{expected_count}<" in page


def test_custom_period_is_inclusive(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    start = (ids["today"] - timedelta(days=7)).isoformat()
    end = (ids["today"] - timedelta(days=6)).isoformat()

    page = client.get(
        f"/estadisticas?periodo=personalizado&desde={start}&hasta={end}"
    ).get_data(as_text=True)

    assert "Período personalizado" in page
    assert "$ 120.00" in page
    assert ">2<" in page


@pytest.mark.parametrize(
    "query",
    [
        "periodo=personalizado&desde=fecha&hasta=2026-01-01",
        "periodo=personalizado&desde=2026-02-01&hasta=2026-01-01",
        "periodo=personalizado&desde=2026-01-01",
        "periodo=desconocido",
    ],
)
def test_invalid_period_falls_back_without_server_error(app, client, query):
    _authenticate(client, app.config["TEST_IDS"]["admin_a"])

    response = client.get(f"/estadisticas?{query}")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Se muestran los últimos 30 días" in page
    assert "Últimos 30 días" in page
    assert "$ 440.00" in page


def test_commerce_isolation_applies_to_every_metric(app):
    ids = app.config["TEST_IDS"]
    with app.app_context():
        connection = get_db()
        summary = get_sales_summary(connection, ids["commerce_a"])
        daily = get_daily_sales(connection, ids["commerce_a"])
        selling = get_top_selling_products(connection, ids["commerce_a"])
        profit = get_estimated_profit(connection, ids["commerce_a"])
        profitable = get_top_profitable_products(connection, ids["commerce_a"])
        low_stock = get_low_stock_products(connection, ids["commerce_a"])

    assert summary["total_sold"] == Decimal("460.00")
    assert summary["sale_count"] == 6
    assert sum(row["total_sold"] for row in daily) == Decimal("460.00")
    assert all(row["product_name"] != "Stock secreto B" for row in selling)
    assert profit == Decimal("190.00")
    assert all(row["product_name"] != "Stock secreto B" for row in profitable)
    assert all(row["product_name"] != "Stock secreto B" for row in low_stock)


def test_empty_commerce_has_zero_metrics_and_valid_empty_charts(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_empty"])

    response = client.get("/estadisticas?periodo=todo")
    page = response.get_data(as_text=True)
    chart_data = _chart_data(page)

    assert response.status_code == 200
    assert "$ 0.00" in page
    assert "Cantidad de ventas" in page
    assert "Unidades vendidas" in page
    assert "Todavía no hay ventas en este período" in page
    assert chart_data["daily_sales"] == {"labels": [], "values": []}
    assert chart_data["top_products"] == {"labels": [], "values": []}


def test_dashboard_and_statistics_are_strictly_read_only(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    before = _database_snapshot(app)

    assert client.get("/dashboard").status_code == 200
    assert client.get("/estadisticas?periodo=todo").status_code == 200

    assert _database_snapshot(app) == before
