from flask import Blueprint, render_template

from .auth import role_required

productos_bp = Blueprint("productos", __name__)


@productos_bp.get("/productos")
@role_required("ADMIN")
def index():
    return render_template("placeholder.html", title="Productos")
