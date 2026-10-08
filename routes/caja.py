import sqlite3
from decimal import Decimal, InvalidOperation

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from database.db import get_db

from .auth import login_required

caja_bp = Blueprint("caja", __name__)


@caja_bp.get("/caja")
@login_required
def index():
    connection = get_db()
    commerce_id = g.user["id_comercio"]
    open_cash_register = get_open_cash_register(connection, commerce_id)
    open_summary = None
    last_closed_cash_register = None
    last_closed_summary = None

    if open_cash_register is not None:
        open_summary = get_cash_summary(
            connection,
            open_cash_register["id_caja"],
            open_cash_register,
        )
    else:
        last_closed_cash_register = _get_last_closed_cash_register(
            connection,
            commerce_id,
        )
        if last_closed_cash_register is not None:
            last_closed_summary = get_cash_summary(
                connection,
                last_closed_cash_register["id_caja"],
                last_closed_cash_register,
            )

    return render_template(
        "caja/index.html",
        open_cash_register=open_cash_register,
        open_summary=open_summary,
        last_closed_cash_register=last_closed_cash_register,
        last_closed_summary=last_closed_summary,
    )


@caja_bp.post("/caja/abrir")
@login_required
def open_cash_register():
    amount = _parse_non_negative_amount(request.form.get("monto_inicial"))
    if amount is None:
        flash("El monto inicial debe ser un número mayor o igual a 0.", "danger")
        return redirect(url_for("caja.index"))

    connection = get_db()

    try:
        connection.execute("BEGIN IMMEDIATE")
        current_cash_register = get_open_cash_register(
            connection,
            g.user["id_comercio"],
        )
        if current_cash_register is not None:
            connection.rollback()
            flash("Ya existe una caja abierta para este comercio.", "warning")
            return redirect(url_for("caja.index"))

        connection.execute(
            """
            INSERT INTO caja (
                id_comercio,
                id_usuario_apertura,
                monto_inicial,
                estado
            ) VALUES (?, ?, ?, 'ABIERTA')
            """,
            (
                g.user["id_comercio"],
                g.user["id_usuario"],
                str(amount),
            ),
        )
        connection.commit()
    except sqlite3.DatabaseError:
        connection.rollback()
        flash("No se pudo abrir la caja. No se registraron cambios.", "danger")
        return redirect(url_for("caja.index"))

    flash("Caja abierta correctamente.", "success")
    return redirect(url_for("caja.index"))


@caja_bp.post("/caja/cerrar")
@login_required
def close_cash_register():
    counted_cash = _parse_non_negative_amount(
        request.form.get("efectivo_contado")
    )
    if counted_cash is None:
        flash("El efectivo contado debe ser un número mayor o igual a 0.", "danger")
        return redirect(url_for("caja.index"))

    connection = get_db()

    try:
        connection.execute("BEGIN IMMEDIATE")
        current_cash_register = get_open_cash_register(
            connection,
            g.user["id_comercio"],
        )
        if current_cash_register is None:
            connection.rollback()
            flash("No hay una caja abierta para cerrar.", "warning")
            return redirect(url_for("caja.index"))

        cursor = connection.execute(
            """
            UPDATE caja
            SET
                id_usuario_cierre = ?,
                fecha_cierre = CURRENT_TIMESTAMP,
                efectivo_contado = ?,
                estado = 'CERRADA'
            WHERE
                id_caja = ?
                AND id_comercio = ?
                AND estado = 'ABIERTA'
            """,
            (
                g.user["id_usuario"],
                str(counted_cash),
                current_cash_register["id_caja"],
                g.user["id_comercio"],
            ),
        )
        if cursor.rowcount != 1:
            raise sqlite3.DatabaseError("La caja dejó de estar disponible")
        connection.commit()
    except sqlite3.DatabaseError:
        connection.rollback()
        flash("No se pudo cerrar la caja. No se registraron cambios.", "danger")
        return redirect(url_for("caja.index"))

    flash("Caja cerrada correctamente.", "success")
    return redirect(url_for("caja.index"))


def get_open_cash_register(connection, commerce_id):
    """Obtiene la caja abierta del comercio para reutilizarla en Ventas."""
    return connection.execute(
        """
        SELECT
            c.*,
            ua.nombre AS apertura_nombre,
            ua.apellido AS apertura_apellido,
            uc.nombre AS cierre_nombre,
            uc.apellido AS cierre_apellido
        FROM caja AS c
        JOIN usuario AS ua ON ua.id_usuario = c.id_usuario_apertura
        LEFT JOIN usuario AS uc ON uc.id_usuario = c.id_usuario_cierre
        WHERE c.id_comercio = ? AND c.estado = 'ABIERTA'
        ORDER BY c.fecha_apertura DESC, c.id_caja DESC
        LIMIT 1
        """,
        (commerce_id,),
    ).fetchone()


def get_cash_summary(connection, cash_register_id, cash_register=None):
    """Deriva ventas, efectivo esperado y diferencia sin persistirlos."""
    if cash_register is None:
        cash_register = connection.execute(
            "SELECT * FROM caja WHERE id_caja = ?",
            (cash_register_id,),
        ).fetchone()

    totals = connection.execute(
        """
        SELECT
            COUNT(*) AS cantidad_ventas,
            COALESCE(SUM(total), 0) AS total_vendido,
            COALESCE(SUM(CASE WHEN medio_pago = 'EFECTIVO' THEN total ELSE 0 END), 0)
                AS total_efectivo,
            COALESCE(SUM(CASE WHEN medio_pago = 'DEBITO' THEN total ELSE 0 END), 0)
                AS total_debito,
            COALESCE(SUM(CASE WHEN medio_pago = 'CREDITO' THEN total ELSE 0 END), 0)
                AS total_credito,
            COALESCE(SUM(CASE WHEN medio_pago = 'TRANSFERENCIA' THEN total ELSE 0 END), 0)
                AS total_transferencia
        FROM venta
        WHERE id_caja = ? AND estado = 'COMPLETADA'
        """,
        (cash_register_id,),
    ).fetchone()

    summary = {
        "cantidad_ventas": totals["cantidad_ventas"],
        "total_vendido": _as_decimal(totals["total_vendido"]),
        "total_efectivo": _as_decimal(totals["total_efectivo"]),
        "total_debito": _as_decimal(totals["total_debito"]),
        "total_credito": _as_decimal(totals["total_credito"]),
        "total_transferencia": _as_decimal(totals["total_transferencia"]),
    }
    summary["efectivo_esperado"] = (
        _as_decimal(cash_register["monto_inicial"])
        + summary["total_efectivo"]
    )
    summary["diferencia"] = None
    if cash_register["efectivo_contado"] is not None:
        summary["diferencia"] = (
            _as_decimal(cash_register["efectivo_contado"])
            - summary["efectivo_esperado"]
        )

    return summary


def _get_last_closed_cash_register(connection, commerce_id):
    return connection.execute(
        """
        SELECT
            c.*,
            ua.nombre AS apertura_nombre,
            ua.apellido AS apertura_apellido,
            uc.nombre AS cierre_nombre,
            uc.apellido AS cierre_apellido
        FROM caja AS c
        JOIN usuario AS ua ON ua.id_usuario = c.id_usuario_apertura
        JOIN usuario AS uc ON uc.id_usuario = c.id_usuario_cierre
        WHERE c.id_comercio = ? AND c.estado = 'CERRADA'
        ORDER BY c.fecha_cierre DESC, c.id_caja DESC
        LIMIT 1
        """,
        (commerce_id,),
    ).fetchone()


def _parse_non_negative_amount(value):
    try:
        amount = Decimal((value or "").strip())
    except (InvalidOperation, AttributeError):
        return None

    if not amount.is_finite() or amount < 0:
        return None

    return amount


def _as_decimal(value):
    return Decimal(str(value or 0))
