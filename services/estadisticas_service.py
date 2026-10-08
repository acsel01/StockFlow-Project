"""Consultas agregadas de solo lectura para Dashboard y Estadísticas."""

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


MONEY_QUANTUM = Decimal("0.01")
PERIOD_LABELS = {
    "hoy": "Hoy",
    "7d": "Últimos 7 días",
    "30d": "Últimos 30 días",
    "mes": "Mes actual",
    "todo": "Todo el historial",
    "personalizado": "Período personalizado",
}


def resolve_period(period="30d", date_from=None, date_to=None, today=None):
    """Valida un período y devuelve límites inclusivos para fechas de Venta."""
    current_date = today or date.today()
    selected_period = period or "30d"

    if selected_period == "hoy":
        start = current_date
        end = current_date
    elif selected_period == "7d":
        start = current_date - timedelta(days=6)
        end = current_date
    elif selected_period == "30d":
        start = current_date - timedelta(days=29)
        end = current_date
    elif selected_period == "mes":
        start = current_date.replace(day=1)
        end = current_date
    elif selected_period == "todo":
        start = None
        end = None
    elif selected_period == "personalizado":
        if not date_from or not date_to:
            raise ValueError("El período personalizado requiere ambas fechas.")
        try:
            start = date.fromisoformat(date_from)
            end = date.fromisoformat(date_to)
        except ValueError:
            raise ValueError("Las fechas deben tener formato YYYY-MM-DD.") from None
        if start > end:
            raise ValueError("La fecha desde no puede ser posterior a la fecha hasta.")
    else:
        raise ValueError("El período seleccionado no es válido.")

    return {
        "key": selected_period,
        "label": PERIOD_LABELS[selected_period],
        "date_from": start,
        "date_to": end,
    }


def get_sales_summary(connection, commerce_id, date_from=None, date_to=None):
    """Calcula total, cantidad, ticket promedio y unidades del período."""
    date_clause, parameters = _date_filter(date_from, date_to)
    sale_totals = connection.execute(
        f"""
        SELECT
            COUNT(v.id_venta) AS sale_count,
            COALESCE(SUM(v.total), 0) AS total_sold
        FROM venta AS v
        JOIN caja AS c ON c.id_caja = v.id_caja
        WHERE
            c.id_comercio = ?
            AND v.estado = 'COMPLETADA'
            {date_clause}
        """,
        [commerce_id, *parameters],
    ).fetchone()
    unit_totals = connection.execute(
        f"""
        SELECT COALESCE(SUM(d.cantidad), 0) AS units_sold
        FROM detalle_venta AS d
        JOIN venta AS v ON v.id_venta = d.id_venta
        JOIN caja AS c ON c.id_caja = v.id_caja
        WHERE
            c.id_comercio = ?
            AND v.estado = 'COMPLETADA'
            {date_clause}
        """,
        [commerce_id, *parameters],
    ).fetchone()

    sale_count = sale_totals["sale_count"]
    total_sold = _money(sale_totals["total_sold"])
    average_ticket = (
        _money(total_sold / sale_count)
        if sale_count
        else Decimal("0.00")
    )
    return {
        "total_sold": total_sold,
        "sale_count": sale_count,
        "average_ticket": average_ticket,
        "units_sold": unit_totals["units_sold"],
    }


def get_daily_sales(connection, commerce_id, date_from=None, date_to=None):
    """Agrupa ventas completadas por fecha de Venta."""
    date_clause, parameters = _date_filter(date_from, date_to)
    rows = connection.execute(
        f"""
        SELECT
            DATE(v.fecha_hora) AS sale_date,
            COUNT(v.id_venta) AS sale_count,
            COALESCE(SUM(v.total), 0) AS total_sold
        FROM venta AS v
        JOIN caja AS c ON c.id_caja = v.id_caja
        WHERE
            c.id_comercio = ?
            AND v.estado = 'COMPLETADA'
            {date_clause}
        GROUP BY DATE(v.fecha_hora)
        ORDER BY DATE(v.fecha_hora)
        """,
        [commerce_id, *parameters],
    ).fetchall()
    return [
        {
            "sale_date": row["sale_date"],
            "sale_count": row["sale_count"],
            "total_sold": _money(row["total_sold"]),
        }
        for row in rows
    ]


def get_top_selling_products(
    connection,
    commerce_id,
    date_from=None,
    date_to=None,
    limit=5,
):
    """Ordena productos por unidades históricas vendidas."""
    date_clause, parameters = _date_filter(date_from, date_to)
    rows = connection.execute(
        f"""
        SELECT
            p.id_producto,
            p.nombre AS product_name,
            SUM(d.cantidad) AS units_sold,
            COALESCE(SUM(d.subtotal), 0) AS total_sold
        FROM detalle_venta AS d
        JOIN venta AS v ON v.id_venta = d.id_venta
        JOIN caja AS c ON c.id_caja = v.id_caja
        JOIN producto AS p ON p.id_producto = d.id_producto
        WHERE
            c.id_comercio = ?
            AND v.estado = 'COMPLETADA'
            {date_clause}
        GROUP BY p.id_producto, p.nombre
        ORDER BY units_sold DESC, total_sold DESC, p.id_producto
        LIMIT ?
        """,
        [commerce_id, *parameters, limit],
    ).fetchall()
    return [
        {
            "id_producto": row["id_producto"],
            "product_name": row["product_name"],
            "units_sold": row["units_sold"],
            "total_sold": _money(row["total_sold"]),
        }
        for row in rows
    ]


def get_estimated_profit(connection, commerce_id, date_from=None, date_to=None):
    """Estima ganancia histórica usando el costo de compra actual."""
    date_clause, parameters = _date_filter(date_from, date_to)
    row = connection.execute(
        f"""
        SELECT COALESCE(
            SUM(d.subtotal - (p.precio_compra * d.cantidad)),
            0
        ) AS estimated_profit
        FROM detalle_venta AS d
        JOIN venta AS v ON v.id_venta = d.id_venta
        JOIN caja AS c ON c.id_caja = v.id_caja
        JOIN producto AS p ON p.id_producto = d.id_producto
        WHERE
            c.id_comercio = ?
            AND v.estado = 'COMPLETADA'
            {date_clause}
        """,
        [commerce_id, *parameters],
    ).fetchone()
    return _money(row["estimated_profit"])


def get_top_profitable_products(
    connection,
    commerce_id,
    date_from=None,
    date_to=None,
    limit=5,
):
    """Ordena productos por ganancia estimada con costo actual."""
    date_clause, parameters = _date_filter(date_from, date_to)
    rows = connection.execute(
        f"""
        SELECT
            p.id_producto,
            p.nombre AS product_name,
            SUM(d.cantidad) AS units_sold,
            COALESCE(SUM(d.subtotal), 0) AS total_sold,
            COALESCE(
                SUM(d.subtotal - (p.precio_compra * d.cantidad)),
                0
            ) AS estimated_profit
        FROM detalle_venta AS d
        JOIN venta AS v ON v.id_venta = d.id_venta
        JOIN caja AS c ON c.id_caja = v.id_caja
        JOIN producto AS p ON p.id_producto = d.id_producto
        WHERE
            c.id_comercio = ?
            AND v.estado = 'COMPLETADA'
            {date_clause}
        GROUP BY p.id_producto, p.nombre
        ORDER BY estimated_profit DESC, units_sold DESC, p.id_producto
        LIMIT ?
        """,
        [commerce_id, *parameters, limit],
    ).fetchall()
    return [
        {
            "id_producto": row["id_producto"],
            "product_name": row["product_name"],
            "units_sold": row["units_sold"],
            "total_sold": _money(row["total_sold"]),
            "estimated_profit": _money(row["estimated_profit"]),
        }
        for row in rows
    ]


def get_low_stock_products(connection, commerce_id, limit=None):
    """Devuelve el stock bajo actual de productos activos."""
    limit_clause = "LIMIT ?" if limit is not None else ""
    parameters = [commerce_id]
    if limit is not None:
        parameters.append(limit)
    rows = connection.execute(
        f"""
        SELECT
            p.id_producto,
            p.nombre AS product_name,
            p.codigo_barras,
            i.stock_actual AS current_stock,
            i.stock_minimo AS minimum_stock
        FROM inventario AS i
        JOIN producto AS p ON p.id_producto = i.id_producto
        WHERE
            p.id_comercio = ?
            AND p.activo = 1
            AND i.stock_actual <= i.stock_minimo
        ORDER BY i.stock_actual, p.nombre
        {limit_clause}
        """,
        parameters,
    ).fetchall()
    return [dict(row) for row in rows]


def get_cash_register_sales_summary(connection, commerce_id, cash_register_id):
    """Resume las ventas completadas de una Caja del comercio."""
    row = connection.execute(
        """
        SELECT
            COUNT(v.id_venta) AS sale_count,
            COALESCE(SUM(v.total), 0) AS total_sold
        FROM caja AS c
        LEFT JOIN venta AS v
            ON v.id_caja = c.id_caja
            AND v.estado = 'COMPLETADA'
        WHERE c.id_caja = ? AND c.id_comercio = ?
        """,
        (cash_register_id, commerce_id),
    ).fetchone()
    return {
        "sale_count": row["sale_count"],
        "total_sold": _money(row["total_sold"]),
    }


def _date_filter(date_from, date_to):
    if date_from is None and date_to is None:
        return "", []
    if date_from is None or date_to is None:
        raise ValueError("Los límites del período deben estar completos.")
    return (
        "AND DATE(v.fecha_hora) BETWEEN ? AND ?",
        [date_from.isoformat(), date_to.isoformat()],
    )


def _money(value):
    return Decimal(str(value or 0)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
