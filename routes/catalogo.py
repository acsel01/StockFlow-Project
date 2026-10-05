from flask import Blueprint, render_template

catalogo_bp = Blueprint("catalogo", __name__)


@catalogo_bp.get("/catalogo")
def index():
    return render_template("placeholder.html", title="Catálogo público")
