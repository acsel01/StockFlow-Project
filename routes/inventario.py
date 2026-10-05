from flask import Blueprint, render_template

inventario_bp = Blueprint("inventario", __name__)


@inventario_bp.get("/inventario")
def index():
    return render_template("placeholder.html", title="Inventario")
