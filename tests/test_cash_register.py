from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from database.db import get_db
from routes.caja import get_cash_summary, get_open_cash_register


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
        vendor_a = _insert_user(
            connection,
            commerce_a,
            "Vendedor A",
            "VENDEDOR",
        )
        admin_b = _insert_user(connection, commerce_b, "Admin B", "ADMIN")
        connection.commit()

    app.config["TEST_IDS"] = {
        "commerce_a": commerce_a,
        "commerce_b": commerce_b,
        "admin_a": admin_a,
        "vendor_a": vendor_a,
        "admin_b": admin_b,
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


def _authenticate(client, user_id):
    with client.session_transaction() as user_session:
        user_session["user_id"] = user_id


def _open(client, amount="1000"):
    return client.post("/caja/abrir", data={"monto_inicial": amount})


def _close(client, amount="1000"):
    return client.post("/caja/cerrar", data={"efectivo_contado": amount})


def _cash_registers(app):
    with app.app_context():
        return [
            dict(row)
            for row in get_db().execute(
                "SELECT * FROM caja ORDER BY id_caja"
            ).fetchall()
        ]


def _insert_sale(
    connection,
    cash_register_id,
    user_id,
    total,
    payment_method,
    received=None,
    change=None,
):
    return connection.execute(
        """
        INSERT INTO venta (
            id_caja,
            id_usuario,
            subtotal,
            descuento,
            total,
            medio_pago,
            dinero_recibido,
            vuelto,
            estado
        ) VALUES (?, ?, ?, 0, ?, ?, ?, ?, 'COMPLETADA')
        """,
        (
            cash_register_id,
            user_id,
            total,
            total,
            payment_method,
            received,
            change,
        ),
    ).lastrowid


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/caja"),
        ("POST", "/caja/abrir"),
        ("POST", "/caja/cerrar"),
    ],
)
def test_cash_register_routes_require_login(client, method, path):
    response = client.open(path, method=method)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


@pytest.mark.parametrize("user_key", ["admin_a", "vendor_a"])
def test_admin_and_vendor_can_view_cash_register(app, client, user_key):
    _authenticate(client, app.config["TEST_IDS"][user_key])

    response = client.get("/caja")

    assert response.status_code == 200
    assert "Sin caja abierta" in response.get_data(as_text=True)


@pytest.mark.parametrize("user_key", ["admin_a", "vendor_a"])
def test_admin_and_vendor_can_open_cash_register(app, client, user_key):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids[user_key])

    response = _open(client, "1250.50")

    assert response.status_code == 302
    cash_register = _cash_registers(app)[0]
    assert cash_register["id_comercio"] == ids["commerce_a"]
    assert cash_register["id_usuario_apertura"] == ids[user_key]
    assert cash_register["id_usuario_cierre"] is None
    assert cash_register["fecha_apertura"] is not None
    assert cash_register["fecha_cierre"] is None
    assert cash_register["monto_inicial"] == 1250.5
    assert cash_register["efectivo_contado"] is None
    assert cash_register["estado"] == "ABIERTA"


@pytest.mark.parametrize("amount", ["", "texto", "-0.01", "NaN", "Infinity"])
def test_opening_rejects_invalid_amount(app, client, amount):
    _authenticate(client, app.config["TEST_IDS"]["admin_a"])

    response = _open(client, amount)

    assert response.status_code == 302
    assert _cash_registers(app) == []
    with client.session_transaction() as user_session:
        assert any(
            "monto inicial" in message.lower()
            for _, message in user_session.get("_flashes", [])
        )


def test_only_one_open_cash_register_per_commerce(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    _open(client, "100")

    response = _open(client, "900")

    assert response.status_code == 302
    registers = _cash_registers(app)
    assert len(registers) == 1
    assert registers[0]["monto_inicial"] == 100


def test_different_commerces_can_each_open_a_cash_register(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    _open(client, "100")
    _authenticate(client, ids["admin_b"])

    _open(client, "200")

    registers = _cash_registers(app)
    assert len(registers) == 2
    assert {row["id_comercio"] for row in registers} == {
        ids["commerce_a"],
        ids["commerce_b"],
    }


def test_cash_register_view_and_close_are_isolated_by_commerce(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_b"])
    _open(client, "8765.43")
    _authenticate(client, ids["admin_a"])

    page = client.get("/caja").get_data(as_text=True)
    response = _close(client, "8765.43")

    assert "Sin caja abierta" in page
    assert "8765.43" not in page
    assert response.status_code == 302
    register = _cash_registers(app)[0]
    assert register["id_comercio"] == ids["commerce_b"]
    assert register["estado"] == "ABIERTA"


def test_summary_uses_sale_total_and_only_cash_for_expected_amount(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    _open(client, "1000")
    cash_register_id = _cash_registers(app)[0]["id_caja"]

    with app.app_context():
        connection = get_db()
        _insert_sale(
            connection,
            cash_register_id,
            ids["admin_a"],
            700,
            "EFECTIVO",
            received=1000,
            change=300,
        )
        _insert_sale(connection, cash_register_id, ids["admin_a"], 200, "DEBITO")
        _insert_sale(connection, cash_register_id, ids["admin_a"], 300, "CREDITO")
        _insert_sale(
            connection,
            cash_register_id,
            ids["admin_a"],
            400,
            "TRANSFERENCIA",
        )
        connection.commit()
        summary = get_cash_summary(connection, cash_register_id)

    assert summary["cantidad_ventas"] == 4
    assert summary["total_vendido"] == Decimal("1600")
    assert summary["total_efectivo"] == Decimal("700")
    assert summary["total_debito"] == Decimal("200")
    assert summary["total_credito"] == Decimal("300")
    assert summary["total_transferencia"] == Decimal("400")
    assert summary["efectivo_esperado"] == Decimal("1700")
    page = client.get("/caja").get_data(as_text=True)
    assert "$ 1700.00" in page


@pytest.mark.parametrize("user_key", ["admin_a", "vendor_a"])
def test_admin_and_vendor_can_close_cash_register(app, client, user_key):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    _open(client, "400")
    _authenticate(client, ids[user_key])

    response = _close(client, "410.25")

    assert response.status_code == 302
    register = _cash_registers(app)[0]
    assert register["id_usuario_cierre"] == ids[user_key]
    assert register["fecha_cierre"] is not None
    assert register["efectivo_contado"] == 410.25
    assert register["estado"] == "CERRADA"


@pytest.mark.parametrize("amount", ["", "texto", "-1", "NaN", "Infinity"])
def test_closing_rejects_invalid_count_and_keeps_cash_register_open(
    app,
    client,
    amount,
):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    _open(client)

    response = _close(client, amount)

    assert response.status_code == 302
    register = _cash_registers(app)[0]
    assert register["estado"] == "ABIERTA"
    assert register["efectivo_contado"] is None


def test_closing_without_open_cash_register_does_not_create_records(app, client):
    _authenticate(client, app.config["TEST_IDS"]["admin_a"])

    response = _close(client, "100")

    assert response.status_code == 302
    assert _cash_registers(app) == []


def test_closed_cash_register_is_immutable_and_next_opening_creates_a_record(
    app,
    client,
):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    _open(client, "100")
    _close(client, "100")

    _close(client, "999")
    _open(client, "250")

    registers = _cash_registers(app)
    assert len(registers) == 2
    assert registers[0]["estado"] == "CERRADA"
    assert registers[0]["efectivo_contado"] == 100
    assert registers[1]["estado"] == "ABIERTA"
    assert registers[1]["monto_inicial"] == 250


@pytest.mark.parametrize(
    ("counted", "expected_difference", "label"),
    [
        ("100", Decimal("0"), "Cierre exacto"),
        ("125", Decimal("25"), "Sobrante de efectivo"),
        ("80", Decimal("-20"), "Faltante de efectivo"),
    ],
)
def test_closing_difference_is_derived(
    app,
    client,
    counted,
    expected_difference,
    label,
):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    _open(client, "100")
    cash_register_id = _cash_registers(app)[0]["id_caja"]

    _close(client, counted)

    with app.app_context():
        summary = get_cash_summary(get_db(), cash_register_id)
    assert summary["diferencia"] == expected_difference
    assert label in client.get("/caja").get_data(as_text=True)


def test_opening_rolls_back_when_database_insert_fails(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    with app.app_context():
        connection = get_db()
        connection.execute(
            """
            CREATE TRIGGER fail_cash_opening
            BEFORE INSERT ON caja
            BEGIN
                SELECT RAISE(ABORT, 'opening failure');
            END
            """
        )
        connection.commit()

    response = _open(client, "100")

    assert response.status_code == 302
    assert _cash_registers(app) == []
    with client.session_transaction() as user_session:
        assert any(
            "No se registraron cambios" in message
            for _, message in user_session.get("_flashes", [])
        )


def test_closing_rolls_back_when_database_update_fails(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_a"])
    _open(client, "100")
    with app.app_context():
        connection = get_db()
        connection.execute(
            """
            CREATE TRIGGER fail_cash_closing
            BEFORE UPDATE ON caja
            BEGIN
                SELECT RAISE(ABORT, 'closing failure');
            END
            """
        )
        connection.commit()

    response = _close(client, "100")

    assert response.status_code == 302
    register = _cash_registers(app)[0]
    assert register["estado"] == "ABIERTA"
    assert register["id_usuario_cierre"] is None
    assert register["efectivo_contado"] is None


def test_concurrent_openings_leave_only_one_open_cash_register(app):
    user_id = app.config["TEST_IDS"]["admin_a"]
    barrier = Barrier(2)

    def attempt_opening(amount):
        with app.test_client() as concurrent_client:
            _authenticate(concurrent_client, user_id)
            barrier.wait()
            return _open(concurrent_client, amount).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(attempt_opening, ("100", "200")))

    assert statuses == [302, 302]
    registers = _cash_registers(app)
    assert len(registers) == 1
    assert registers[0]["estado"] == "ABIERTA"


def test_open_cash_register_lookup_is_scoped_to_commerce(app, client):
    ids = app.config["TEST_IDS"]
    _authenticate(client, ids["admin_b"])
    _open(client, "300")

    with app.app_context():
        connection = get_db()
        assert get_open_cash_register(connection, ids["commerce_a"]) is None
        register = get_open_cash_register(connection, ids["commerce_b"])

    assert register["id_comercio"] == ids["commerce_b"]
    assert register["apertura_nombre"] == "Admin B"
