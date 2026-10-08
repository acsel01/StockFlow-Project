from flask import Blueprint, render_template

from .auth import login_required

inventario_bp = Blueprint("inventario", __name__)


@inventario_bp.get("/inventario")
@login_required
def index():
    return render_template("placeholder.html", title="Inventario")
