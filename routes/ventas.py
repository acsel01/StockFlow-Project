from flask import Blueprint, render_template

ventas_bp = Blueprint("ventas", __name__)


@ventas_bp.get("/punto-venta")
def punto_venta():
    return render_template("placeholder.html", title="Punto de venta")


@ventas_bp.get("/ventas")
def historial():
    return render_template("placeholder.html", title="Historial de ventas")
