import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from database.db import get_db


USERS = {
    "admin": ("admin@example.com", "admin-password"),
    "vendor": ("vendor@example.com", "vendor-password"),
    "inactive": ("inactive@example.com", "inactive-password"),
}


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "DATABASE": str(tmp_path / "test.db"),
    })

    with app.app_context():
        connection = get_db()
        commerce = connection.execute(
            "INSERT INTO comercio (nombre, direccion) VALUES (?, ?)",
            ("Comercio de prueba", "Calle de prueba 123"),
        )
        commerce_id = commerce.lastrowid

        connection.executemany(
            """
            INSERT INTO usuario (
                id_comercio, nombre, email, password_hash, rol, activo
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    commerce_id,
                    "Administrador",
                    USERS["admin"][0],
                    generate_password_hash(USERS["admin"][1]),
                    "ADMIN",
                    1,
                ),
                (
                    commerce_id,
                    "Vendedor",
                    USERS["vendor"][0],
                    generate_password_hash(USERS["vendor"][1]),
                    "VENDEDOR",
                    1,
                ),
                (
                    commerce_id,
                    "Inactivo",
                    USERS["inactive"][0],
                    generate_password_hash(USERS["inactive"][1]),
                    "VENDEDOR",
                    0,
                ),
            ],
        )
        connection.commit()

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def log_in(client, user_type, password=None):
    email, valid_password = USERS[user_type]
    return client.post(
        "/login",
        data={
            "email": email,
            "password": password if password is not None else valid_password,
        },
    )


@pytest.mark.parametrize("user_type", ["admin", "vendor"])
def test_active_user_can_log_in(client, user_type):
    response = log_in(client, user_type)

    assert response.status_code == 302
    assert response.headers["Location"] == "/dashboard"

    with client.session_transaction() as user_session:
        assert "user_id" in user_session


@pytest.mark.parametrize(
    ("email", "password"),
    [
        (USERS["admin"][0], "wrong-password"),
        ("missing@example.com", "any-password"),
        USERS["inactive"],
    ],
    ids=["wrong-password", "missing-user", "inactive-user"],
)
def test_invalid_credentials_do_not_log_in(client, email, password):
    response = client.post(
        "/login",
        data={"email": email, "password": password},
    )

    assert response.status_code == 200
    assert "Email o contraseña incorrectos." in response.get_data(as_text=True)

    with client.session_transaction() as user_session:
        assert "user_id" not in user_session


def test_logout_clears_the_session(client):
    log_in(client, "admin")

    response = client.post("/logout")

    assert response.status_code == 302
    assert response.headers["Location"] == "/login"

    with client.session_transaction() as user_session:
        assert len(user_session) == 0


@pytest.mark.parametrize(
    "path",
    [
        "/dashboard",
        "/productos",
        "/estadisticas",
        "/inventario",
        "/punto-venta",
        "/ventas",
        "/caja",
    ],
)
def test_internal_routes_require_login(client, path):
    response = client.get(path)

    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


@pytest.mark.parametrize("path", ["/productos", "/estadisticas"])
def test_admin_can_access_admin_routes(client, path):
    log_in(client, "admin")

    response = client.get(path)

    assert response.status_code == 200


@pytest.mark.parametrize("path", ["/productos", "/estadisticas"])
def test_vendor_cannot_access_admin_routes(client, path):
    log_in(client, "vendor")

    response = client.get(path)

    assert response.status_code == 403


@pytest.mark.parametrize(
    "path",
    ["/dashboard", "/inventario", "/punto-venta", "/ventas", "/caja"],
)
def test_vendor_can_access_operational_routes(client, path):
    log_in(client, "vendor")

    response = client.get(path)

    assert response.status_code == 200


def test_catalog_remains_public(client):
    response = client.get("/catalogo")

    assert response.status_code == 200


def test_session_only_stores_user_id(client):
    log_in(client, "admin")

    with client.session_transaction() as user_session:
        assert set(user_session) == {"user_id"}
        assert "password" not in user_session
        assert "password_hash" not in user_session
