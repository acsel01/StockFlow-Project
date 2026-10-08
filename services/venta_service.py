"""Operaciones transaccionales relacionadas con ventas."""

import sqlite3
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


PAYMENT_METHODS = ("EFECTIVO", "DEBITO", "CREDITO", "TRANSFERENCIA")
MONEY_QUANTUM = Decimal("0.01")


class VentaError(Exception):
    """Error funcional que puede mostrarse al usuario del futuro POS."""


def confirmar_venta(
    connection,
    caja_id,
    usuario_id,
    items,
    medio_pago,
    dinero_recibido=None,
    observaciones=None,
):
    """Confirma Venta, detalles, stock y movimientos en una transacción."""
    try:
        connection.execute("BEGIN IMMEDIATE")
        user = _get_active_user(connection, usuario_id)
        cash_register = _get_valid_cash_register(
            connection,
            caja_id,
            user["id_comercio"],
        )
        normalized_items = _normalize_items(items)
        sale_lines = _load_sale_lines(
            connection,
            normalized_items,
            cash_register["id_comercio"],
        )
        payment_method = _validate_payment_method(medio_pago)
        subtotal = _money(sum(line["subtotal"] for line in sale_lines))
        total = subtotal
        received, change = _validate_payment(
            payment_method,
            dinero_recibido,
            total,
        )

        sale_id = connection.execute(
            """
            INSERT INTO venta (
                id_caja,
                id_usuario,
                subtotal,
                descuento,
                total,
                medio_pago,
                dinero_recibido,
                vuelto,
                estado,
                observaciones
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'COMPLETADA', ?)
            """,
            (
                cash_register["id_caja"],
                user["id_usuario"],
                str(subtotal),
                "0.00",
                str(total),
                payment_method,
                str(received) if received is not None else None,
                str(change) if change is not None else None,
                observaciones,
            ),
        ).lastrowid

        for line in sale_lines:
            connection.execute(
                """
                INSERT INTO detalle_venta (
                    id_venta,
                    id_producto,
                    cantidad,
                    precio_unitario,
                    subtotal
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    sale_id,
                    line["id_producto"],
                    line["cantidad"],
                    str(line["precio_unitario"]),
                    str(line["subtotal"]),
                ),
            )
            cursor = connection.execute(
                """
                UPDATE inventario
                SET
                    stock_actual = ?,
                    ultima_actualizacion = CURRENT_TIMESTAMP
                WHERE id_inventario = ? AND stock_actual = ?
                """,
                (
                    line["stock_resultante"],
                    line["id_inventario"],
                    line["stock_anterior"],
                ),
            )
            if cursor.rowcount != 1:
                raise VentaError(
                    f"El stock de {line['producto_nombre']} cambió; intentá nuevamente."
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
                ) VALUES (?, ?, ?, 'VENTA', ?, ?, ?, ?)
                """,
                (
                    line["id_inventario"],
                    user["id_usuario"],
                    sale_id,
                    -line["cantidad"],
                    f"Venta #{sale_id}",
                    line["stock_anterior"],
                    line["stock_resultante"],
                ),
            )

        connection.commit()
    except VentaError:
        connection.rollback()
        raise
    except sqlite3.DatabaseError as error:
        connection.rollback()
        raise VentaError(
            "No se pudo confirmar la venta. No se registraron cambios."
        ) from error

    return {
        "id_venta": sale_id,
        "subtotal": subtotal,
        "descuento": Decimal("0.00"),
        "total": total,
        "medio_pago": payment_method,
        "dinero_recibido": received,
        "vuelto": change,
    }


def _get_active_user(connection, user_id):
    user = connection.execute(
        """
        SELECT id_usuario, id_comercio, activo
        FROM usuario
        WHERE id_usuario = ?
        """,
        (user_id,),
    ).fetchone()
    if user is None or not user["activo"]:
        raise VentaError("El usuario no está habilitado para confirmar ventas.")
    return user


def _get_valid_cash_register(connection, cash_register_id, commerce_id):
    cash_register = connection.execute(
        """
        SELECT id_caja, id_comercio, estado
        FROM caja
        WHERE id_caja = ?
        """,
        (cash_register_id,),
    ).fetchone()
    if (
        cash_register is None
        or cash_register["estado"] != "ABIERTA"
        or cash_register["id_comercio"] != commerce_id
    ):
        raise VentaError("No hay una caja abierta válida.")
    return cash_register


def _normalize_items(items):
    if not isinstance(items, (list, tuple)) or not items:
        raise VentaError("La venta debe incluir al menos un producto.")

    normalized = {}
    for item in items:
        if not isinstance(item, dict):
            raise VentaError("Cada producto debe tener un identificador y una cantidad.")

        product_id = _positive_integer(
            item.get("id_producto"),
            "El producto indicado no es válido.",
        )
        quantity = _positive_integer(
            item.get("cantidad"),
            "La cantidad debe ser un número entero mayor a cero.",
        )
        normalized[product_id] = normalized.get(product_id, 0) + quantity

    return normalized


def _positive_integer(value, message):
    if isinstance(value, bool):
        raise VentaError(message)
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = int(value.strip())
        except (TypeError, ValueError):
            raise VentaError(message) from None
    else:
        raise VentaError(message)

    if parsed <= 0:
        raise VentaError(message)
    return parsed


def _load_sale_lines(connection, normalized_items, commerce_id):
    lines = []
    for product_id, quantity in normalized_items.items():
        product = connection.execute(
            """
            SELECT
                p.id_producto,
                p.id_comercio,
                p.nombre,
                p.precio_venta,
                p.activo,
                i.id_inventario,
                i.stock_actual
            FROM producto AS p
            LEFT JOIN inventario AS i ON i.id_producto = p.id_producto
            WHERE p.id_producto = ?
            """,
            (product_id,),
        ).fetchone()

        if product is None or product["id_inventario"] is None:
            raise VentaError("El producto indicado no existe.")
        if product["id_comercio"] != commerce_id:
            raise VentaError("El producto no pertenece a este comercio.")
        if not product["activo"]:
            raise VentaError(f"El producto {product['nombre']} está inactivo.")
        if quantity > product["stock_actual"]:
            raise VentaError(f"Stock insuficiente para {product['nombre']}.")

        unit_price = _money(product["precio_venta"])
        line_subtotal = _money(unit_price * quantity)
        lines.append({
            "id_producto": product["id_producto"],
            "producto_nombre": product["nombre"],
            "id_inventario": product["id_inventario"],
            "cantidad": quantity,
            "precio_unitario": unit_price,
            "subtotal": line_subtotal,
            "stock_anterior": product["stock_actual"],
            "stock_resultante": product["stock_actual"] - quantity,
        })

    return lines


def _validate_payment_method(payment_method):
    if payment_method not in PAYMENT_METHODS:
        raise VentaError("El medio de pago no es válido.")
    return payment_method


def _validate_payment(payment_method, received_value, total):
    if payment_method != "EFECTIVO":
        return None, None

    try:
        received = _money(received_value)
    except (InvalidOperation, TypeError, ValueError):
        raise VentaError("El efectivo recibido debe ser un importe válido.") from None

    if not received.is_finite() or received < total:
        raise VentaError("El efectivo recibido es insuficiente.")
    return received, _money(received - total)


def _money(value):
    amount = value if isinstance(value, Decimal) else Decimal(str(value))
    if not amount.is_finite():
        raise InvalidOperation
    return amount.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
