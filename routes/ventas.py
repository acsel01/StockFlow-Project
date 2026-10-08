from flask import Blueprint, render_template

from .auth import login_required

ventas_bp = Blueprint("ventas", __name__)


@ventas_bp.get("/punto-venta")
@login_required
def punto_venta():
    return render_template("placeholder.html", title="Punto de venta")


@ventas_bp.get("/ventas")
@login_required
def historial():
    return render_template("placeholder.html", title="Historial de ventas")
