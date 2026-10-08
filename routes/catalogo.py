from flask import Blueprint, abort, render_template, request

from database.db import get_db
from services.catalogo_service import (
    get_public_catalog,
    get_public_categories,
    get_public_commerce,
    get_public_commerces,
)

catalogo_bp = Blueprint("catalogo", __name__)


@catalogo_bp.get("/catalogo")
def index():
    return render_template(
        "catalogo/comercios.html",
        commerces=get_public_commerces(get_db()),
    )


@catalogo_bp.get("/catalogo/<int:commerce_id>")
def commerce_catalog(commerce_id):
    connection = get_db()
    commerce = get_public_commerce(connection, commerce_id)
    if commerce is None:
        abort(404)

    search = request.args.get("q", "").strip()
    categories = get_public_categories(connection, commerce_id)
    category_ids = {category["id_categoria"] for category in categories}
    selected_category = None
    invalid_category = False
    raw_category = request.args.get("categoria", "").strip()
    if raw_category:
        try:
            requested_category = int(raw_category)
        except ValueError:
            requested_category = None
        if requested_category in category_ids:
            selected_category = requested_category
        else:
            invalid_category = True

    products = get_public_catalog(
        connection,
        commerce_id,
        search=search,
        category_id=selected_category,
    )
    return render_template(
        "catalogo/index.html",
        commerce=commerce,
        products=products,
        categories=categories,
        search=search,
        selected_category=selected_category,
        invalid_category=invalid_category,
    )
