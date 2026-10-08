from flask import Blueprint, abort, g, render_template, request

from database.db import get_db

from .auth import login_required

ventas_bp = Blueprint("ventas", __name__)


@ventas_bp.get("/punto-venta")
@login_required
def punto_venta():
    return render_template("placeholder.html", title="Punto de venta")


@ventas_bp.get("/ventas")
@login_required
def historial():
    payment_method = request.args.get("medio_pago", "").strip()
    parameters = [g.user["id_comercio"]]
    payment_condition = ""
    if payment_method in ("EFECTIVO", "DEBITO", "CREDITO", "TRANSFERENCIA"):
        payment_condition = "AND v.medio_pago = ?"
        parameters.append(payment_method)
    else:
        payment_method = ""

    sales = get_db().execute(
        f"""
        SELECT
            v.id_venta,
            v.fecha_hora,
            v.medio_pago,
            v.total,
            v.estado,
            v.id_caja,
            u.nombre AS vendedor_nombre,
            u.apellido AS vendedor_apellido,
            COUNT(d.id_detalle_venta) AS cantidad_productos,
            COALESCE(SUM(d.cantidad), 0) AS cantidad_unidades
        FROM venta AS v
        JOIN caja AS c ON c.id_caja = v.id_caja
        JOIN usuario AS u ON u.id_usuario = v.id_usuario
        LEFT JOIN detalle_venta AS d ON d.id_venta = v.id_venta
        WHERE c.id_comercio = ? {payment_condition}
        GROUP BY v.id_venta
        ORDER BY v.fecha_hora DESC, v.id_venta DESC
        """,
        parameters,
    ).fetchall()

    return render_template(
        "ventas/index.html",
        sales=sales,
        payment_methods=("EFECTIVO", "DEBITO", "CREDITO", "TRANSFERENCIA"),
        selected_payment_method=payment_method,
    )


@ventas_bp.get("/ventas/<int:sale_id>")
@login_required
def detail(sale_id):
    connection = get_db()
    sale = connection.execute(
        """
        SELECT
            v.*,
            u.nombre AS vendedor_nombre,
            u.apellido AS vendedor_apellido
        FROM venta AS v
        JOIN caja AS c ON c.id_caja = v.id_caja
        JOIN usuario AS u ON u.id_usuario = v.id_usuario
        WHERE v.id_venta = ? AND c.id_comercio = ?
        """,
        (sale_id, g.user["id_comercio"]),
    ).fetchone()
    if sale is None:
        abort(404)

    lines = connection.execute(
        """
        SELECT
            d.id_detalle_venta,
            d.cantidad,
            d.precio_unitario,
            d.subtotal,
            p.nombre AS producto_nombre,
            p.codigo_barras
        FROM detalle_venta AS d
        JOIN producto AS p ON p.id_producto = d.id_producto
        WHERE d.id_venta = ?
        ORDER BY d.id_detalle_venta
        """,
        (sale_id,),
    ).fetchall()

    return render_template("ventas/detalle.html", sale=sale, lines=lines)
