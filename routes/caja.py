from flask import Blueprint, render_template

from .auth import login_required

caja_bp = Blueprint("caja", __name__)


@caja_bp.get("/caja")
@login_required
def index():
    return render_template("placeholder.html", title="Caja")
