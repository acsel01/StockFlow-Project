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
        commerce_a = connection.execute(
            "INSERT INTO comercio (nombre, direccion) VALUES (?, ?)",
            ("Comercio A", "Dirección A"),
        ).lastrowid
        commerce_b = connection.execute(
            "INSERT INTO comercio (nombre, direccion) VALUES (?, ?)",
            ("Comercio B", "Dirección B"),
        ).lastrowid

        admin_a = connection.execute(
            """
            INSERT INTO usuario (
                id_comercio, nombre, email, password_hash, rol
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (commerce_a, "Admin A", "admin-a@example.com", PASSWORD_HASH, "ADMIN"),
        ).lastrowid
        vendor_a = connection.execute(
            """
            INSERT INTO usuario (
                id_comercio, nombre, email, password_hash, rol
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (commerce_a, "Vendedor A", "vendor-a@example.com", PASSWORD_HASH, "VENDEDOR"),
        ).lastrowid

        category_a = connection.execute(
            """
            INSERT INTO categoria (id_comercio, nombre, descripcion)
            VALUES (?, ?, ?)
            """,
            (commerce_a, "Bebidas", "Bebidas del comercio A"),
        ).lastrowid
        second_category_a = connection.execute(
            """
            INSERT INTO categoria (id_comercio, nombre)
            VALUES (?, ?)
            """,
            (commerce_a, "Almacén"),
        ).lastrowid
        category_b = connection.execute(
            """
            INSERT INTO categoria (id_comercio, nombre)
            VALUES (?, ?)
            """,
            (commerce_b, "Categoría secreta"),
        ).lastrowid

        product_a = _insert_product(
            connection,
            commerce_a,
            category_a,
            "Coca Cola",
            "A-100",
        )
        second_product_a = _insert_product(
            connection,
            commerce_a,
            second_category_a,
            "Galletitas",
            "A-200",
        )
        product_b = _insert_product(
            connection,
            commerce_b,
            category_b,
            "Producto secreto",
            "B-100",
        )
        connection.commit()

    app.config["TEST_IDS"] = {
        "commerce_a": commerce_a,
        "commerce_b": commerce_b,
        "admin_a": admin_a,
        "vendor_a": vendor_a,
        "category_a": category_a,
        "second_category_a": second_category_a,
        "category_b": category_b,
        "product_a": product_a,
        "second_product_a": second_product_a,
        "product_b": product_b,
    }
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _insert_product(connection, commerce_id, category_id, name, barcode):
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
            mostrar_precio_catalogo
        ) VALUES (?, ?, ?, ?, 10, 15, 1, 0)
        """,
        (commerce_id, category_id, name, barcode),
    ).lastrowid
    connection.execute(
        "INSERT INTO inventario (id_producto) VALUES (?)",
        (product_id,),
    )
    return product_id


def _authenticate(client, user_id):
    with client.session_transaction() as user_session:
        user_session["user_id"] = user_id


def _product_form(category_id, name="Producto nuevo", barcode="NEW-100"):
    return {
        "nombre": name,
        "descripcion": "Descripción de prueba",
        "id_categoria": str(category_id),
        "codigo_barras": barcode or "",
        "precio_compra": "20.50",
        "precio_venta": "30.75",
        "imagen_url": "https://example.com/producto.jpg",
        "activo": "on",
    }


@pytest.mark.parametrize(
    ("user_key", "expected_status"),
    [("admin_a", 200), ("vendor_a", 403)],
)
def test_product_access_depends_on_role(app, client, user_key, expected_status):
    _authenticate(client, app.config["TEST_IDS"][user_key])

    response = client.get("/productos")

    assert response.status_code == expected_status


def test_product_list_is_limited_to_current_commerce(app, client):
    _authenticate(client, app.config["TEST_IDS"]["admin_a"])

    response = client.get("/productos")
    page = response.get_data(as_text=True)

    assert "Coca Cola" in page
    assert "Galletitas" in page
    assert "Producto secreto" not in page


def test_search_finds_product_by_name(app, client):
    _authenticate(client, app.config["TEST_IDS"]["admin_a"])

    page = client.get("/productos?q=coca").get_data(as_text=True)

    assert "Coca Cola" in page
    assert "Galletitas" not in page


def test_search_finds_barcode_without_leaking_other_commerce(app, client):
    _authenticate(client, app.config["TEST_IDS"]["admin_a"])

    own_page = client.get("/productos?q=A-200").get_data(as_text=True)
    other_page = client.get("/productos?q=B-100").get_data(as_text=True)

    assert "Galletitas" in own_page
    assert "Coca Cola" not in own_page
    assert "Producto secreto" not in other_page


def test_create_product_also_creates_zero_inventory(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    form = _product_form(ids["category_a"])
    form.update({"visible_catalogo": "on", "stock_actual": "99"})

    response = client.post("/productos/nuevo", data=form)

    assert response.status_code == 302

    with app.app_context():
        row = get_db().execute(
            """
            SELECT p.*, i.stock_actual, i.stock_minimo
            FROM producto AS p
            JOIN inventario AS i ON i.id_producto = p.id_producto
            WHERE p.nombre = ?
            """,
            ("Producto nuevo",),
        ).fetchone()

        assert row["id_comercio"] == ids["commerce_a"]
        assert row["stock_actual"] == 0
        assert row["stock_minimo"] == 0
        assert row["visible_catalogo"] == 1
        assert row["mostrar_precio_catalogo"] == 0


def test_create_product_rolls_back_when_inventory_fails(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    with app.app_context():
        connection = get_db()
        connection.execute(
            """
            CREATE TRIGGER fail_new_inventory
            BEFORE INSERT ON inventario
            BEGIN
                SELECT RAISE(ABORT, 'inventory failure');
            END
            """
        )
        connection.commit()

    response = client.post(
        "/productos/nuevo",
        data=_product_form(ids["category_a"], name="Producto incompleto"),
    )

    assert response.status_code == 200
    assert "No se pudo crear el producto" in response.get_data(as_text=True)

    with app.app_context():
        product = get_db().execute(
            "SELECT 1 FROM producto WHERE nombre = ?",
            ("Producto incompleto",),
        ).fetchone()
        assert product is None


def test_product_name_is_required(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    form = _product_form(ids["category_a"])
    form["nombre"] = " "

    response = client.post("/productos/nuevo", data=form)

    assert response.status_code == 200
    assert "El nombre es obligatorio." in response.get_data(as_text=True)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("precio_compra", "-1", "precio de compra"),
        ("precio_venta", "-1", "precio de venta"),
        ("precio_compra", "texto", "precio de compra"),
        ("precio_venta", "", "precio de venta"),
    ],
)
def test_invalid_prices_are_rejected(app, client, field, value, message):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    form = _product_form(ids["category_a"])
    form[field] = value

    response = client.post("/productos/nuevo", data=form)

    assert response.status_code == 200
    assert message in response.get_data(as_text=True)


def test_duplicate_barcode_in_same_commerce_is_rejected(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    response = client.post(
        "/productos/nuevo",
        data=_product_form(ids["category_a"], barcode="A-100"),
    )

    assert response.status_code == 200
    assert "Ya existe un producto con ese código de barras." in response.get_data(
        as_text=True
    )


def test_multiple_products_can_have_null_barcode(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    first = client.post(
        "/productos/nuevo",
        data=_product_form(ids["category_a"], name="Sin código 1", barcode=""),
    )
    second = client.post(
        "/productos/nuevo",
        data=_product_form(ids["category_a"], name="Sin código 2", barcode="   "),
    )

    assert first.status_code == 302
    assert second.status_code == 302

    with app.app_context():
        count = get_db().execute(
            """
            SELECT COUNT(*)
            FROM producto
            WHERE id_comercio = ? AND codigo_barras IS NULL
            """,
            (ids["commerce_a"],),
        ).fetchone()[0]
        assert count == 2


@pytest.mark.parametrize("category_key", ["category_b", None])
def test_invalid_or_foreign_category_is_rejected(app, client, category_key):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    category_id = ids[category_key] if category_key else 99999

    response = client.post(
        "/productos/nuevo",
        data=_product_form(category_id),
    )

    assert response.status_code == 200
    assert "categoría activa de tu comercio" in response.get_data(as_text=True)


def test_edit_product_updates_only_commercial_data(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    form = _product_form(
        ids["second_category_a"],
        name="Coca Cola editada",
        barcode="A-101",
    )
    form["mostrar_precio_catalogo"] = "on"
    form["stock_actual"] = "500"

    response = client.post(
        f"/productos/{ids['product_a']}/editar",
        data=form,
    )

    assert response.status_code == 302

    with app.app_context():
        row = get_db().execute(
            """
            SELECT p.*, i.stock_actual, i.stock_minimo
            FROM producto AS p
            JOIN inventario AS i ON i.id_producto = p.id_producto
            WHERE p.id_producto = ?
            """,
            (ids["product_a"],),
        ).fetchone()
        assert row["nombre"] == "Coca Cola editada"
        assert row["id_categoria"] == ids["second_category_a"]
        assert row["codigo_barras"] == "A-101"
        assert row["mostrar_precio_catalogo"] == 1
        assert row["stock_actual"] == 0
        assert row["stock_minimo"] == 0


@pytest.mark.parametrize("method", ["get", "post"])
def test_admin_cannot_edit_product_from_other_commerce(app, client, method):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    path = f"/productos/{ids['product_b']}/editar"

    if method == "get":
        response = client.get(path)
    else:
        response = client.post(path, data=_product_form(ids["category_a"]))

    assert response.status_code == 404


def test_product_uses_soft_deactivation_and_can_be_reactivated(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    deactivate = client.post(f"/productos/{ids['product_a']}/desactivar")

    assert deactivate.status_code == 302

    with app.app_context():
        connection = get_db()
        product = connection.execute(
            "SELECT activo FROM producto WHERE id_producto = ?",
            (ids["product_a"],),
        ).fetchone()
        inventory = connection.execute(
            "SELECT 1 FROM inventario WHERE id_producto = ?",
            (ids["product_a"],),
        ).fetchone()
        assert product["activo"] == 0
        assert inventory is not None

    activate = client.post(f"/productos/{ids['product_a']}/activar")

    assert activate.status_code == 302

    with app.app_context():
        active = get_db().execute(
            "SELECT activo FROM producto WHERE id_producto = ?",
            (ids["product_a"],),
        ).fetchone()[0]
        assert active == 1


@pytest.mark.parametrize(
    ("visible", "show_price"),
    [(False, False), (False, True), (True, False), (True, True)],
)
def test_catalog_flags_are_stored_independently(app, client, visible, show_price):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    name = f"Banderas {int(visible)}-{int(show_price)}"
    form = _product_form(ids["category_a"], name=name, barcode=None)

    if visible:
        form["visible_catalogo"] = "on"
    if show_price:
        form["mostrar_precio_catalogo"] = "on"

    response = client.post("/productos/nuevo", data=form)

    assert response.status_code == 302

    with app.app_context():
        row = get_db().execute(
            """
            SELECT visible_catalogo, mostrar_precio_catalogo
            FROM producto
            WHERE nombre = ?
            """,
            (name,),
        ).fetchone()
        assert row["visible_catalogo"] == int(visible)
        assert row["mostrar_precio_catalogo"] == int(show_price)


def test_create_category_for_current_commerce(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    response = client.post(
        "/categorias",
        data={"nombre": "Limpieza", "descripcion": "Artículos de limpieza"},
    )

    assert response.status_code == 302

    with app.app_context():
        category = get_db().execute(
            "SELECT * FROM categoria WHERE nombre = ?",
            ("Limpieza",),
        ).fetchone()
        assert category["id_comercio"] == ids["commerce_a"]
        assert category["activa"] == 1


def test_duplicate_category_name_is_rejected(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    response = client.post("/categorias", data={"nombre": "bebidas"})

    assert response.status_code == 200
    assert "Ya existe una categoría con ese nombre." in response.get_data(as_text=True)


def test_deactivate_category_keeps_existing_products(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    response = client.post(f"/categorias/{ids['category_a']}/desactivar")

    assert response.status_code == 302

    with app.app_context():
        connection = get_db()
        category = connection.execute(
            "SELECT activa FROM categoria WHERE id_categoria = ?",
            (ids["category_a"],),
        ).fetchone()
        product = connection.execute(
            "SELECT id_categoria FROM producto WHERE id_producto = ?",
            (ids["product_a"],),
        ).fetchone()
        assert category["activa"] == 0
        assert product["id_categoria"] == ids["category_a"]


def test_categories_are_isolated_by_commerce(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])

    page = client.get("/categorias").get_data(as_text=True)
    response = client.post(f"/categorias/{ids['category_b']}/desactivar")

    assert "Bebidas" in page
    assert "Categoría secreta" not in page
    assert response.status_code == 404

    with app.app_context():
        active = get_db().execute(
            "SELECT activa FROM categoria WHERE id_categoria = ?",
            (ids["category_b"],),
        ).fetchone()[0]
        assert active == 1
