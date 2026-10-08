from copy import deepcopy

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from database.db import get_db
from services.catalogo_service import get_public_catalog
from services.venta_service import confirmar_venta


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
        commerce_a = _insert_commerce(
            connection,
            "Comercio Público A",
            active=1,
            neighborhood="Centro",
            locality="Córdoba",
        )
        commerce_b = _insert_commerce(connection, "Comercio Público B", active=1)
        commerce_empty = _insert_commerce(connection, "Comercio Vacío", active=1)
        inactive_commerce = _insert_commerce(
            connection,
            "Comercio Inactivo Secreto",
            active=0,
        )
        vendor_a = _insert_user(connection, commerce_a, "Vendedor A")
        beverages = _insert_category(connection, commerce_a, "Bebidas")
        foods = _insert_category(connection, commerce_a, "Alimentos")
        inactive_category = _insert_category(
            connection,
            commerce_a,
            "Categoría Archivada",
            active=0,
        )
        unused_category = _insert_category(connection, commerce_a, "Sin publicaciones")
        category_b = _insert_category(connection, commerce_b, "Categoría B")

        public_priced, public_priced_inventory = _insert_product(
            connection,
            commerce_a,
            beverages,
            "Yerba pública",
            description="Descripción pública de yerba",
            image_url="https://example.test/yerba.jpg",
            purchase_price="987654.32",
            sale_price="100.00",
            stock=4321,
            minimum_stock=1234,
            visible=1,
            show_price=1,
        )
        public_hidden_price, hidden_price_inventory = _insert_product(
            connection,
            commerce_a,
            beverages,
            "Producto precio oculto",
            purchase_price="1.00",
            sale_price="876543.21",
            stock=1,
            minimum_stock=3,
            visible=1,
            show_price=0,
        )
        depleted, depleted_inventory = _insert_product(
            connection,
            commerce_a,
            beverages,
            "Producto agotado público",
            purchase_price="5.00",
            sale_price="50.00",
            stock=0,
            minimum_stock=2,
            visible=1,
            show_price=1,
        )
        foods_product, foods_inventory = _insert_product(
            connection,
            commerce_a,
            foods,
            "Galletitas públicas",
            purchase_price="10.00",
            sale_price="25.50",
            stock=5,
            minimum_stock=2,
            visible=1,
            show_price=1,
        )
        hidden_both, hidden_both_inventory = _insert_product(
            connection,
            commerce_a,
            beverages,
            "Oculto ambos flags",
            purchase_price="10.00",
            sale_price="333333.33",
            stock=5,
            minimum_stock=2,
            visible=0,
            show_price=0,
        )
        hidden_with_price, hidden_with_price_inventory = _insert_product(
            connection,
            commerce_a,
            beverages,
            "Oculto aunque precio habilitado",
            image_url="https://secret.test/hidden.jpg",
            purchase_price="10.00",
            sale_price="222222.22",
            stock=5,
            minimum_stock=2,
            visible=0,
            show_price=1,
        )
        inactive_product, inactive_product_inventory = _insert_product(
            connection,
            commerce_a,
            beverages,
            "Producto inactivo visible",
            purchase_price="10.00",
            sale_price="444444.44",
            stock=5,
            minimum_stock=2,
            visible=1,
            show_price=1,
            active=0,
        )
        inactive_category_product, inactive_category_inventory = _insert_product(
            connection,
            commerce_a,
            inactive_category,
            "Producto de categoría inactiva",
            purchase_price="10.00",
            sale_price="555555.55",
            stock=5,
            minimum_stock=2,
            visible=1,
            show_price=1,
        )
        no_inventory_product, _ = _insert_product(
            connection,
            commerce_a,
            unused_category,
            "Producto sin inventario",
            purchase_price="10.00",
            sale_price="666666.66",
            stock=0,
            minimum_stock=0,
            visible=1,
            show_price=1,
            create_inventory=False,
        )
        sale_product, sale_product_inventory = _insert_product(
            connection,
            commerce_a,
            foods,
            "Producto integración venta",
            purchase_price="40.00",
            sale_price="100.00",
            stock=2,
            minimum_stock=1,
            visible=1,
            show_price=1,
        )
        foreign_product, foreign_inventory = _insert_product(
            connection,
            commerce_b,
            category_b,
            "Producto exclusivo B",
            description="SECRETO-COMERCIO-B",
            image_url="https://secret.test/b.jpg",
            purchase_price="777777.77",
            sale_price="999999.99",
            stock=9876,
            minimum_stock=1234,
            visible=1,
            show_price=1,
        )
        open_cash_a = _insert_cash_register(connection, commerce_a, vendor_a)
        connection.commit()

    app.config["TEST_IDS"] = {
        "commerce_a": commerce_a,
        "commerce_b": commerce_b,
        "commerce_empty": commerce_empty,
        "inactive_commerce": inactive_commerce,
        "vendor_a": vendor_a,
        "beverages": beverages,
        "foods": foods,
        "inactive_category": inactive_category,
        "unused_category": unused_category,
        "category_b": category_b,
        "public_priced": public_priced,
        "public_priced_inventory": public_priced_inventory,
        "public_hidden_price": public_hidden_price,
        "hidden_price_inventory": hidden_price_inventory,
        "depleted": depleted,
        "depleted_inventory": depleted_inventory,
        "foods_product": foods_product,
        "foods_inventory": foods_inventory,
        "hidden_both": hidden_both,
        "hidden_both_inventory": hidden_both_inventory,
        "hidden_with_price": hidden_with_price,
        "hidden_with_price_inventory": hidden_with_price_inventory,
        "inactive_product": inactive_product,
        "inactive_product_inventory": inactive_product_inventory,
        "inactive_category_product": inactive_category_product,
        "inactive_category_inventory": inactive_category_inventory,
        "no_inventory_product": no_inventory_product,
        "sale_product": sale_product,
        "sale_product_inventory": sale_product_inventory,
        "foreign_product": foreign_product,
        "foreign_inventory": foreign_inventory,
        "open_cash_a": open_cash_a,
    }
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _insert_commerce(
    connection,
    name,
    active,
    neighborhood=None,
    locality=None,
):
    return connection.execute(
        """
        INSERT INTO comercio (
            nombre, direccion, barrio, localidad, activo
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (name, f"Dirección de {name}", neighborhood, locality, active),
    ).lastrowid


def _insert_user(connection, commerce_id, name):
    return connection.execute(
        """
        INSERT INTO usuario (
            id_comercio, nombre, email, password_hash, rol
        ) VALUES (?, ?, ?, ?, 'VENDEDOR')
        """,
        (commerce_id, name, "vendor-a@example.com", PASSWORD_HASH),
    ).lastrowid


def _insert_category(connection, commerce_id, name, active=1):
    return connection.execute(
        """
        INSERT INTO categoria (id_comercio, nombre, activa)
        VALUES (?, ?, ?)
        """,
        (commerce_id, name, active),
    ).lastrowid


def _insert_product(
    connection,
    commerce_id,
    category_id,
    name,
    purchase_price,
    sale_price,
    stock,
    minimum_stock,
    visible,
    show_price,
    description=None,
    image_url=None,
    active=1,
    create_inventory=True,
):
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
            imagen_url,
            visible_catalogo,
            mostrar_precio_catalogo,
            activo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            commerce_id,
            category_id,
            name,
            description,
            f"CODE-{name}",
            purchase_price,
            sale_price,
            image_url,
            visible,
            show_price,
            active,
        ),
    ).lastrowid
    inventory_id = None
    if create_inventory:
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
        ) VALUES (?, ?, 0, 'ABIERTA')
        """,
        (commerce_id, user_id),
    ).lastrowid


def _catalog_path(app, query=""):
    path = f"/catalogo/{app.config['TEST_IDS']['commerce_a']}"
    return f"{path}?{query}" if query else path


def _product_card(page, product_name):
    name_index = page.index(product_name)
    start = page.rfind("<article", 0, name_index)
    end = page.index("</article>", name_index) + len("</article>")
    return page[start:end]


def _database_snapshot(app):
    tables = ("comercio", "categoria", "producto", "inventario", "caja", "venta")
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


def test_public_catalog_entry_and_store_need_no_login(app, client):
    response = client.get("/catalogo")
    store = client.get(_catalog_path(app))

    assert response.status_code == 200
    assert store.status_code == 200
    assert "Catálogos públicos" in response.get_data(as_text=True)
    assert "Yerba pública" in store.get_data(as_text=True)


def test_selector_lists_only_active_commerces(app, client):
    page = client.get("/catalogo").get_data(as_text=True)

    assert "Comercio Público A" in page
    assert "Comercio Público B" in page
    assert "Comercio Vacío" in page
    assert "Comercio Inactivo Secreto" not in page


@pytest.mark.parametrize("commerce_key", [None, "inactive_commerce"])
def test_missing_or_inactive_commerce_returns_404(app, client, commerce_key):
    ids = app.config["TEST_IDS"]
    commerce_id = 999999 if commerce_key is None else ids[commerce_key]

    response = client.get(f"/catalogo/{commerce_id}")

    assert response.status_code == 404


def test_public_product_projection_shows_only_approved_information(app, client):
    page = client.get(_catalog_path(app)).get_data(as_text=True)

    assert "Yerba pública" in page
    assert "Descripción pública de yerba" in page
    assert "Bebidas" in page
    assert "https://example.test/yerba.jpg" in page
    assert 'alt="Yerba pública"' in page
    assert "$ 100.00" in page
    assert "Disponible" in page


def test_public_html_does_not_leak_cost_or_exact_stock_sentinels(app, client):
    page = client.get(_catalog_path(app)).get_data(as_text=True).lower()

    for secret in (
        "987654.32",
        "4321",
        "1234",
        "precio_compra",
        "stock_actual",
        "stock_minimo",
        "margen",
        "ganancia",
        "id_usuario",
        "id_caja",
        "id_inventario",
        "id_venta",
    ):
        assert secret not in page
    assert "data-stock" not in page
    assert "data-minimum" not in page


@pytest.mark.parametrize(
    ("product_name", "visible", "show_price", "must_appear"),
    [
        ("Oculto ambos flags", 0, 0, False),
        ("Oculto aunque precio habilitado", 0, 1, False),
        ("Producto precio oculto", 1, 0, True),
        ("Yerba pública", 1, 1, True),
    ],
)
def test_issue_17_flag_combinations(
    app,
    client,
    product_name,
    visible,
    show_price,
    must_appear,
):
    page = client.get(_catalog_path(app)).get_data(as_text=True)

    assert (product_name in page) is must_appear
    if visible and not show_price:
        assert "Precio no publicado" in page
    if visible and show_price and product_name == "Yerba pública":
        assert "$ 100.00" in page


def test_hidden_price_is_never_embedded_in_public_html(app, client):
    page = client.get(_catalog_path(app)).get_data(as_text=True)

    assert "Producto precio oculto" in page
    assert "Precio no publicado" in page
    assert "876543.21" not in page


def test_hidden_product_reveals_no_name_price_or_image(app, client):
    page = client.get(_catalog_path(app)).get_data(as_text=True)

    assert "Oculto aunque precio habilitado" not in page
    assert "222222.22" not in page
    assert "https://secret.test/hidden.jpg" not in page


def test_inactive_product_and_inactive_category_are_not_public(app, client):
    page = client.get(_catalog_path(app)).get_data(as_text=True)

    assert "Producto inactivo visible" not in page
    assert "Producto de categoría inactiva" not in page
    assert "Categoría Archivada" not in page
    assert "444444.44" not in page
    assert "555555.55" not in page


def test_deactivating_category_hides_its_products_and_public_filter(app, client):
    ids = app.config["TEST_IDS"]
    initial = client.get(_catalog_path(app)).get_data(as_text=True)
    assert "Galletitas públicas" in initial
    assert "Alimentos" in initial

    with app.app_context():
        connection = get_db()
        connection.execute(
            "UPDATE categoria SET activa = 0 WHERE id_categoria = ?",
            (ids["foods"],),
        )
        connection.commit()

    page = client.get(_catalog_path(app)).get_data(as_text=True)
    assert "Galletitas públicas" not in page
    assert "Producto integración venta" not in page
    assert "Alimentos" not in page


def test_product_without_inventory_is_not_exposed(app, client):
    page = client.get(_catalog_path(app)).get_data(as_text=True)

    assert "Producto sin inventario" not in page
    assert "Sin publicaciones" not in page
    assert "666666.66" not in page


def test_all_three_derived_availability_states_are_shown(app, client):
    page = client.get(_catalog_path(app)).get_data(as_text=True)

    assert "Disponible" in page
    assert "Pocas unidades" in page
    assert "Agotado" in page


def test_inventory_changes_are_reflected_on_each_catalog_request(app, client):
    ids = app.config["TEST_IDS"]
    initial = client.get(_catalog_path(app)).get_data(as_text=True)
    assert "Disponible" in _product_card(initial, "Yerba pública")

    with app.app_context():
        connection = get_db()
        connection.execute(
            "UPDATE inventario SET stock_actual = 1000 WHERE id_inventario = ?",
            (ids["public_priced_inventory"],),
        )
        connection.commit()
    low_page = client.get(_catalog_path(app)).get_data(as_text=True)
    yerba_card = _product_card(low_page, "Yerba pública")
    assert "Pocas unidades" in yerba_card

    with app.app_context():
        connection = get_db()
        connection.execute(
            "UPDATE inventario SET stock_actual = 0 WHERE id_inventario = ?",
            (ids["public_priced_inventory"],),
        )
        connection.commit()
    depleted_page = client.get(_catalog_path(app)).get_data(as_text=True)
    yerba_card = _product_card(depleted_page, "Yerba pública")
    assert "Agotado" in yerba_card


def test_current_sale_price_change_is_reflected_publicly(app, client):
    ids = app.config["TEST_IDS"]
    initial = client.get(_catalog_path(app)).get_data(as_text=True)
    assert "$ 100.00" in _product_card(initial, "Yerba pública")
    with app.app_context():
        connection = get_db()
        connection.execute(
            "UPDATE producto SET precio_venta = 150 WHERE id_producto = ?",
            (ids["public_priced"],),
        )
        connection.commit()

    page = client.get(_catalog_path(app)).get_data(as_text=True)
    yerba_card = _product_card(page, "Yerba pública")

    assert "$ 150.00" in yerba_card
    assert "$ 100.00" not in yerba_card


def test_name_search_is_partial_and_never_reveals_hidden_products(app, client):
    public_page = client.get(
        _catalog_path(app, "q=gallet")
    ).get_data(as_text=True)
    hidden_page = client.get(
        _catalog_path(app, "q=ambos")
    ).get_data(as_text=True)

    assert "Galletitas públicas" in public_page
    assert "Yerba pública" not in public_page
    assert "No se encontraron productos" in hidden_page
    assert "Oculto ambos flags" not in hidden_page
    assert "Oculto aunque precio habilitado" not in hidden_page


def test_valid_category_filter_only_shows_that_public_category(app, client):
    ids = app.config["TEST_IDS"]

    page = client.get(
        _catalog_path(app, f"categoria={ids['foods']}")
    ).get_data(as_text=True)

    assert "Galletitas públicas" in page
    assert "Producto integración venta" in page
    assert "Yerba pública" not in page


def test_foreign_or_invalid_category_is_ignored_safely(app, client):
    ids = app.config["TEST_IDS"]

    foreign_page = client.get(
        _catalog_path(app, f"categoria={ids['category_b']}")
    ).get_data(as_text=True)
    invalid_page = client.get(
        _catalog_path(app, "categoria=texto")
    ).get_data(as_text=True)

    for page in (foreign_page, invalid_page):
        assert "categoría indicada no está disponible" in page
        assert "Yerba pública" in page
        assert "Producto exclusivo B" not in page


def test_catalog_is_isolated_between_active_commerces(app, client):
    ids = app.config["TEST_IDS"]
    page_a = client.get(_catalog_path(app)).get_data(as_text=True)
    page_b = client.get(f"/catalogo/{ids['commerce_b']}").get_data(as_text=True)

    assert "Producto exclusivo B" not in page_a
    assert "SECRETO-COMERCIO-B" not in page_a
    assert "999999.99" not in page_a
    assert "9876" not in page_a
    assert "Producto exclusivo B" in page_b
    assert "Yerba pública" not in page_b


def test_catalog_rejects_product_linked_to_category_from_another_commerce(
    app,
    client,
):
    ids = app.config["TEST_IDS"]
    with app.app_context():
        connection = get_db()
        inconsistent_product = connection.execute(
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, 1)
            """,
            (
                ids["commerce_a"],
                ids["category_b"],
                "PRODUCTO-INCONSISTENTE-ENTRE-COMERCIOS",
                "DESCRIPCION-CENTINELA-ENTRE-COMERCIOS",
                "CODIGO-INCONSISTENTE-ENTRE-COMERCIOS",
                "1.00",
                "765432.10",
            ),
        ).lastrowid
        connection.execute(
            """
            INSERT INTO inventario (id_producto, stock_actual, stock_minimo)
            VALUES (?, 10, 1)
            """,
            (inconsistent_product,),
        )
        connection.commit()

    page = client.get(_catalog_path(app)).get_data(as_text=True)

    assert "PRODUCTO-INCONSISTENTE-ENTRE-COMERCIOS" not in page
    assert "DESCRIPCION-CENTINELA-ENTRE-COMERCIOS" not in page
    assert "765432.10" not in page
    assert "Categoría B" not in page


def test_empty_commerce_has_clear_state(app, client):
    ids = app.config["TEST_IDS"]

    page = client.get(
        f"/catalogo/{ids['commerce_empty']}"
    ).get_data(as_text=True)

    assert "Este comercio todavía no tiene productos publicados" in page


def test_public_projection_contains_no_internal_stock_or_product_ids(app):
    ids = app.config["TEST_IDS"]
    with app.app_context():
        products = get_public_catalog(get_db(), ids["commerce_a"])

    assert products
    assert set(products[0]) == {
        "name",
        "description",
        "image_url",
        "price",
        "category",
        "availability",
    }
    hidden_price = next(
        product
        for product in products
        if product["name"] == "Producto precio oculto"
    )
    assert hidden_price["price"] is None


def test_confirmed_sale_updates_catalog_availability_via_inventory(app, client):
    ids = app.config["TEST_IDS"]
    before = client.get(_catalog_path(app)).get_data(as_text=True)
    product_card = _product_card(before, "Producto integración venta")
    assert "Disponible" in product_card

    with app.app_context():
        confirmar_venta(
            get_db(),
            ids["open_cash_a"],
            ids["vendor_a"],
            [{"id_producto": ids["sale_product"], "cantidad": 1}],
            "EFECTIVO",
            "100",
        )

    after = client.get(_catalog_path(app)).get_data(as_text=True)
    product_card = _product_card(after, "Producto integración venta")
    assert "Pocas unidades" in product_card


def test_public_catalog_requests_are_database_read_only(app, client):
    before = _database_snapshot(app)

    assert client.get("/catalogo").status_code == 200
    assert client.get(_catalog_path(app, "q=yerba")).status_code == 200

    assert _database_snapshot(app) == before
