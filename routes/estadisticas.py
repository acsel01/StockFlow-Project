from flask import Blueprint, render_template

from .auth import role_required

estadisticas_bp = Blueprint("estadisticas", __name__)


@estadisticas_bp.get("/estadisticas")
@role_required("ADMIN")
def index():
    return render_template("placeholder.html", title="Estadísticas")
