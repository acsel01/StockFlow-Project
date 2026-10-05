from flask import Blueprint, render_template

estadisticas_bp = Blueprint("estadisticas", __name__)


@estadisticas_bp.get("/estadisticas")
def index():
    return render_template("placeholder.html", title="Estadísticas")
