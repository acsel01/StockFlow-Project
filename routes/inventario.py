import sqlite3

from flask import (
    Blueprint,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from database.db import get_db
from services.inventario_service import get_availability_status

from .auth import login_required, role_required

inventario_bp = Blueprint("inventario", __name__)

MANUAL_MOVEMENT_TYPES = (
    "REPOSICION",
    "CORRECCION",
    "PERDIDA",
    "CONTEO_FISICO",
    "OTRO",
)
ALL_MOVEMENT_TYPES = ("VENTA", *MANUAL_MOVEMENT_TYPES)


@inventario_bp.get("/inventario")
@login_required
def index():
    search = request.args.get("q", "").strip()
    availability_filter = request.args.get("estado", "").strip()
    parameters = [g.user["id_comercio"]]
    conditions = []

    if search:
        search_value = f"%{search}%"
        conditions.append("(p.nombre LIKE ? OR p.codigo_barras LIKE ?)")
        parameters.extend((search_value, search_value))

    if availability_filter == "bajo":
        conditions.append("i.stock_actual <= i.stock_minimo")

    extra_conditions = ""
    if conditions:
        extra_conditions = "AND " + " AND ".join(conditions)

    rows = get_db().execute(
        f"""
        SELECT
            i.id_inventario,
            i.stock_actual,
            i.stock_minimo,
            i.ultima_actualizacion,
            p.nombre AS producto_nombre,
            p.codigo_barras,
            p.precio_compra,
            p.precio_venta,
            p.activo AS producto_activo,
            c.nombre AS categoria_nombre
        FROM inventario AS i
        JOIN producto AS p ON p.id_producto = i.id_producto
        JOIN categoria AS c ON c.id_categoria = p.id_categoria
        WHERE p.id_comercio = ? {extra_conditions}
        ORDER BY p.nombre
        """,
        parameters,
    ).fetchall()

    inventories = []
    for row in rows:
        inventory = dict(row)
        inventory["availability"] = get_availability_status(
            row["stock_actual"],
            row["stock_minimo"],
        )
        inventories.append(inventory)

    return render_template(
        "inventario/index.html",
        inventories=inventories,
        search=search,
        availability_filter=availability_filter,
    )


@inventario_bp.post("/inventario/<int:inventory_id>/stock-minimo")
@role_required("ADMIN")
def update_minimum_stock(inventory_id):
    _get_inventory(inventory_id)
    value = request.form.get("stock_minimo", "").strip()

    try:
        minimum_stock = int(value)
    except (TypeError, ValueError):
        minimum_stock = -1

    if minimum_stock < 0:
        flash("El stock mínimo debe ser un entero mayor o igual a 0.", "danger")
        return redirect(url_for("inventario.index"))

    connection = get_db()
    connection.execute(
        """
        UPDATE inventario
        SET stock_minimo = ?, ultima_actualizacion = CURRENT_TIMESTAMP
        WHERE id_inventario = ?
        """,
        (minimum_stock, inventory_id),
    )
    connection.commit()
    flash("Stock mínimo actualizado.", "success")
    return redirect(url_for("inventario.index"))


@inventario_bp.route(
    "/inventario/<int:inventory_id>/ajustar",
    methods=("GET", "POST"),
)
@role_required("ADMIN")
def adjust_stock(inventory_id):
    inventory = _get_inventory(inventory_id)
    form = {"tipo": "", "cantidad": "", "motivo": ""}
    error = None

    if request.method == "POST":
        form = {
            "tipo": request.form.get("tipo", "").strip(),
            "cantidad": request.form.get("cantidad", "").strip(),
            "motivo": request.form.get("motivo", "").strip(),
        }
        status, message = apply_stock_movement(
            inventory_id=inventory_id,
            movement_type=form["tipo"],
            entered_value=form["cantidad"],
            reason=form["motivo"] or None,
            user_id=g.user["id_usuario"],
            commerce_id=g.user["id_comercio"],
        )

        if status in ("success", "info"):
            flash(message, status)
            return redirect(url_for("inventario.index"))

        error = message
        inventory = _get_inventory(inventory_id)

    return render_template(
        "inventario/ajustar.html",
        inventory=inventory,
        movement_types=MANUAL_MOVEMENT_TYPES,
        form=form,
        error=error,
    )


@inventario_bp.get("/inventario/movimientos")
@role_required("ADMIN")
def movements():
    search = request.args.get("q", "").strip()
    movement_type = request.args.get("tipo", "").strip()
    parameters = [g.user["id_comercio"]]
    conditions = []

    if search:
        search_value = f"%{search}%"
        conditions.append("(p.nombre LIKE ? OR p.codigo_barras LIKE ?)")
        parameters.extend((search_value, search_value))

    if movement_type in ALL_MOVEMENT_TYPES:
        conditions.append("m.tipo = ?")
        parameters.append(movement_type)

    extra_conditions = ""
    if conditions:
        extra_conditions = "AND " + " AND ".join(conditions)

    movement_rows = get_db().execute(
        f"""
        SELECT
            m.id_movimiento,
            m.fecha_hora,
            m.tipo,
            m.cantidad_delta,
            m.stock_anterior,
            m.stock_resultante,
            m.motivo,
            p.nombre AS producto_nombre,
            p.codigo_barras,
            u.nombre AS usuario_nombre,
            u.apellido AS usuario_apellido
        FROM movimiento_inventario AS m
        JOIN inventario AS i ON i.id_inventario = m.id_inventario
        JOIN producto AS p ON p.id_producto = i.id_producto
        JOIN usuario AS u ON u.id_usuario = m.id_usuario
        WHERE p.id_comercio = ? {extra_conditions}
        ORDER BY m.fecha_hora DESC, m.id_movimiento DESC
        """,
        parameters,
    ).fetchall()

    return render_template(
        "inventario/movimientos.html",
        movements=movement_rows,
        movement_types=ALL_MOVEMENT_TYPES,
        search=search,
        selected_type=movement_type,
    )


def apply_stock_movement(
    inventory_id,
    movement_type,
    entered_value,
    reason,
    user_id,
    commerce_id,
):
    """Actualiza el stock y registra su movimiento en una transacción."""
    if movement_type not in MANUAL_MOVEMENT_TYPES:
        return "error", "Seleccioná un tipo de movimiento manual válido."

    try:
        value = int(entered_value)
    except (TypeError, ValueError):
        return "error", "La cantidad debe ser un número entero."

    connection = get_db()

    try:
        connection.execute("BEGIN IMMEDIATE")
        inventory = _find_inventory(connection, inventory_id, commerce_id)

        if inventory is None:
            connection.rollback()
            abort(404)

        previous_stock = inventory["stock_actual"]
        delta, validation_error = _calculate_delta(
            movement_type,
            value,
            previous_stock,
        )

        if validation_error:
            connection.rollback()
            return "error", validation_error

        if delta == 0:
            connection.rollback()
            return (
                "info",
                "El conteo coincide con el stock actual; no se registraron cambios.",
            )

        resulting_stock = previous_stock + delta
        if resulting_stock < 0:
            connection.rollback()
            return "error", "El movimiento dejaría el stock en negativo."

        connection.execute(
            """
            UPDATE inventario
            SET stock_actual = ?, ultima_actualizacion = CURRENT_TIMESTAMP
            WHERE id_inventario = ?
            """,
            (resulting_stock, inventory_id),
        )
        connection.execute(
            """
            INSERT INTO movimiento_inventario (
                id_inventario,
                id_usuario,
                id_venta,
                tipo,
                cantidad_delta,
                motivo,
                stock_anterior,
                stock_resultante
            ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?)
            """,
            (
                inventory_id,
                user_id,
                movement_type,
                delta,
                reason,
                previous_stock,
                resulting_stock,
            ),
        )
        connection.commit()
    except sqlite3.DatabaseError:
        connection.rollback()
        return "error", "No se pudo registrar el movimiento. El stock no cambió."

    return "success", "Stock actualizado correctamente."


def _calculate_delta(movement_type, value, current_stock):
    if movement_type == "REPOSICION":
        if value <= 0:
            return None, "La reposición debe ser mayor a 0."
        return value, None

    if movement_type == "PERDIDA":
        if value <= 0:
            return None, "La pérdida debe ser mayor a 0."
        return -value, None

    if movement_type in ("CORRECCION", "OTRO"):
        if value == 0:
            return None, "El ajuste debe ser distinto de 0."
        return value, None

    if movement_type == "CONTEO_FISICO":
        if value < 0:
            return None, "El stock contado debe ser mayor o igual a 0."
        return value - current_stock, None

    return None, "Seleccioná un tipo de movimiento manual válido."


def _get_inventory(inventory_id):
    inventory = _find_inventory(
        get_db(),
        inventory_id,
        g.user["id_comercio"],
    )

    if inventory is None:
        abort(404)

    return inventory


def _find_inventory(connection, inventory_id, commerce_id):
    return connection.execute(
        """
        SELECT
            i.id_inventario,
            i.stock_actual,
            i.stock_minimo,
            i.ultima_actualizacion,
            p.id_producto,
            p.nombre AS producto_nombre,
            p.codigo_barras,
            p.activo AS producto_activo,
            c.nombre AS categoria_nombre
        FROM inventario AS i
        JOIN producto AS p ON p.id_producto = i.id_producto
        JOIN categoria AS c ON c.id_categoria = p.id_categoria
        WHERE i.id_inventario = ? AND p.id_comercio = ?
        """,
        (inventory_id, commerce_id),
    ).fetchone()
