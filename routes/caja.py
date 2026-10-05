from flask import Blueprint, render_template

caja_bp = Blueprint("caja", __name__)


@caja_bp.get("/caja")
def index():
    return render_template("placeholder.html", title="Caja")
