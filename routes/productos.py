from flask import Blueprint, render_template

productos_bp = Blueprint("productos", __name__)


@productos_bp.get("/productos")
def index():
    return render_template("placeholder.html", title="Productos")
