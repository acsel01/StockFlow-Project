from html.parser import HTMLParser

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from database.db import get_db


class _NavigationParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.section_links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "a" and "data-section" in attributes:
            self.section_links.append(attributes)


@pytest.fixture
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "ui-navigation-test-key",
            "DATABASE": str(tmp_path / "ui-navigation.db"),
        }
    )

    with app.app_context():
        connection = get_db()
        commerce_id = connection.execute(
            "INSERT INTO comercio (nombre, direccion) VALUES (?, ?)",
            ("Comercio navegación", "Calle interfaz 123"),
        ).lastrowid
        admin_id = connection.execute(
            """
            INSERT INTO usuario (
                id_comercio, nombre, apellido, email, password_hash, rol
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                commerce_id,
                "Ada",
                "Admin",
                "admin-ui@example.com",
                generate_password_hash("admin-password"),
                "ADMIN",
            ),
        ).lastrowid
        vendor_id = connection.execute(
            """
            INSERT INTO usuario (
                id_comercio, nombre, apellido, email, password_hash, rol
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                commerce_id,
                "Vera",
                "Vendedora",
                "vendor-ui@example.com",
                generate_password_hash("vendor-password"),
                "VENDEDOR",
            ),
        ).lastrowid
        connection.commit()

    app.config["UI_USER_IDS"] = {"admin": admin_id, "vendor": vendor_id}
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _authenticate(client, user_id):
    with client.session_transaction() as user_session:
        user_session["user_id"] = user_id


def _get_section_links(page):
    parser = _NavigationParser()
    parser.feed(page)
    return parser.section_links


def _sections(page):
    return {link["data-section"] for link in _get_section_links(page)}


def _assert_active_section(page, expected_section):
    links = _get_section_links(page)
    current_sections = {
        link["data-section"]
        for link in links
        if link.get("aria-current") == "page"
    }
    assert current_sections == {expected_section}


def test_admin_dashboard_exposes_complete_internal_navigation(app, client):
    _authenticate(client, app.config["UI_USER_IDS"]["admin"])

    page = client.get("/dashboard").get_data(as_text=True)

    assert 'data-testid="internal-sidebar"' in page
    assert 'data-bs-target="#sfMobileNavigation"' in page
    assert _sections(page) == {
        "dashboard",
        "pos",
        "cash",
        "inventory",
        "products",
        "sales",
        "statistics",
    }
    _assert_active_section(page, "dashboard")


@pytest.mark.parametrize(
    ("path", "active_section"),
    [("/caja", "cash"), ("/productos", "products")],
)
def test_admin_navigation_persists_and_marks_section(
    app,
    client,
    path,
    active_section,
):
    _authenticate(client, app.config["UI_USER_IDS"]["admin"])

    response = client.get(path)
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert _sections(page) == {
        "dashboard",
        "pos",
        "cash",
        "inventory",
        "products",
        "sales",
        "statistics",
    }
    _assert_active_section(page, active_section)


def test_vendor_navigation_contains_only_operational_sections(app, client):
    _authenticate(client, app.config["UI_USER_IDS"]["vendor"])

    page = client.get("/dashboard").get_data(as_text=True)

    assert _sections(page) == {
        "dashboard",
        "pos",
        "cash",
        "inventory",
        "sales",
    }
    assert 'href="/productos"' not in page
    assert 'href="/estadisticas"' not in page
    assert 'href="/inventario/movimientos"' not in page


def test_public_catalog_uses_public_header_without_internal_sidebar(client):
    page = client.get("/catalogo").get_data(as_text=True)

    assert 'data-testid="internal-sidebar"' not in page
    assert 'aria-label="Navegación pública"' in page
    assert 'href="/catalogo"' in page
    assert 'href="/login"' in page


def test_login_does_not_expose_internal_or_admin_navigation(client):
    page = client.get("/login").get_data(as_text=True)

    assert 'data-testid="internal-sidebar"' not in page
    assert 'data-section="products"' not in page
    assert 'data-section="statistics"' not in page
    assert "Iniciar sesión" in page
