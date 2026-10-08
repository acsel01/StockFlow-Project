from decimal import Decimal

from flask import (
    Blueprint,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from database.db import get_db
from services.venta_service import PAYMENT_METHODS, VentaError, confirmar_venta

from .auth import login_required
from .caja import get_open_cash_register

ventas_bp = Blueprint("ventas", __name__)


@ventas_bp.get("/punto-venta")
@login_required
def punto_venta():
    connection = get_db()
    commerce_id = g.user["id_comercio"]
    search = request.args.get("q", "").strip()
    open_cash_register = get_open_cash_register(connection, commerce_id)
    cart = _get_pos_cart()
    cart_lines, cart_total, cart_has_issues = _load_pos_cart(
        connection,
        commerce_id,
        cart,
    )
    products = _search_pos_products(connection, commerce_id, search)

    return render_template(
        "ventas/punto_venta.html",
        search=search,
        products=products,
        open_cash_register=open_cash_register,
        cart_lines=cart_lines,
        cart_total=cart_total,
        cart_has_issues=cart_has_issues,
        payment_methods=PAYMENT_METHODS,
    )


@ventas_bp.post("/punto-venta/agregar/<int:product_id>")
@login_required
def add_to_cart(product_id):
    quantity = _parse_positive_integer(request.form.get("cantidad", "1"))
    if quantity is None:
        flash("La cantidad debe ser un número entero mayor a cero.", "danger")
        return _redirect_to_pos()

    product = _get_available_pos_product(
        get_db(),
        g.user["id_comercio"],
        product_id,
    )
    if product is None:
        flash("El producto no está disponible para este comercio.", "danger")
        return _redirect_to_pos()

    cart = _get_pos_cart()
    final_quantity = cart.get(str(product_id), 0) + quantity
    if final_quantity > product["stock_actual"]:
        flash(f"Stock insuficiente para {product['nombre']}.", "danger")
        return _redirect_to_pos()

    cart[str(product_id)] = final_quantity
    session["pos_cart"] = cart
    flash("Producto agregado al carrito.", "success")
    return _redirect_to_pos()


@ventas_bp.post("/punto-venta/<int:product_id>/cantidad")
@login_required
def update_cart_quantity(product_id):
    quantity = _parse_positive_integer(request.form.get("cantidad"))
    if quantity is None:
        flash("La cantidad debe ser un número entero mayor a cero.", "danger")
        return redirect(url_for("ventas.punto_venta"))

    product = _get_available_pos_product(
        get_db(),
        g.user["id_comercio"],
        product_id,
    )
    if product is None:
        flash("El producto no está disponible para este comercio.", "danger")
        return redirect(url_for("ventas.punto_venta"))
    if quantity > product["stock_actual"]:
        flash(f"Stock insuficiente para {product['nombre']}.", "danger")
        return redirect(url_for("ventas.punto_venta"))

    cart = _get_pos_cart()
    if str(product_id) not in cart:
        flash("El producto no se encuentra en el carrito.", "warning")
        return redirect(url_for("ventas.punto_venta"))

    cart[str(product_id)] = quantity
    session["pos_cart"] = cart
    flash("Cantidad actualizada.", "success")
    return redirect(url_for("ventas.punto_venta"))


@ventas_bp.post("/punto-venta/<int:product_id>/quitar")
@login_required
def remove_from_cart(product_id):
    cart = _get_pos_cart()
    removed = cart.pop(str(product_id), None)
    session["pos_cart"] = cart
    if removed is None:
        flash("El producto no se encontraba en el carrito.", "info")
    else:
        flash("Producto eliminado.", "success")
    return redirect(url_for("ventas.punto_venta"))


@ventas_bp.post("/punto-venta/cancelar")
@login_required
def cancel_cart():
    session.pop("pos_cart", None)
    flash("Carrito cancelado.", "success")
    return redirect(url_for("ventas.punto_venta"))


@ventas_bp.post("/punto-venta/confirmar")
@login_required
def confirm_pos_sale():
    cart = _get_pos_cart()
    if not cart:
        flash("El carrito está vacío.", "danger")
        return redirect(url_for("ventas.punto_venta"))

    connection = get_db()
    open_cash_register = get_open_cash_register(
        connection,
        g.user["id_comercio"],
    )
    if open_cash_register is None:
        flash("No hay una caja abierta.", "danger")
        return redirect(url_for("ventas.punto_venta"))

    try:
        items = [
            {"id_producto": int(product_id), "cantidad": quantity}
            for product_id, quantity in cart.items()
        ]
    except (TypeError, ValueError):
        flash("El carrito contiene datos inválidos.", "danger")
        return redirect(url_for("ventas.punto_venta"))

    try:
        result = confirmar_venta(
            connection,
            open_cash_register["id_caja"],
            g.user["id_usuario"],
            items,
            request.form.get("medio_pago", ""),
            request.form.get("dinero_recibido"),
            request.form.get("observaciones", "").strip() or None,
        )
    except VentaError as error:
        flash(str(error), "danger")
        return redirect(url_for("ventas.punto_venta"))

    session.pop("pos_cart", None)
    message = (
        f"Venta #{result['id_venta']} confirmada correctamente. "
        f"Total: ${result['total']:.2f}."
    )
    if result["vuelto"] is not None:
        message += f" Vuelto: ${result['vuelto']:.2f}."
    flash(message, "success")
    return redirect(url_for("ventas.detail", sale_id=result["id_venta"]))


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


def _get_pos_cart():
    cart = session.get("pos_cart", {})
    return dict(cart) if isinstance(cart, dict) else {}


def _search_pos_products(connection, commerce_id, search):
    parameters = [commerce_id]
    search_condition = ""
    exact_barcode_order = "1"
    if search:
        search_value = f"%{search}%"
        search_condition = "AND (p.nombre LIKE ? OR p.codigo_barras LIKE ?)"
        exact_barcode_order = "CASE WHEN p.codigo_barras = ? THEN 0 ELSE 1 END"
        parameters.extend((search_value, search_value, search))

    return connection.execute(
        f"""
        SELECT
            p.id_producto,
            p.nombre,
            p.codigo_barras,
            p.precio_venta,
            i.stock_actual
        FROM producto AS p
        JOIN inventario AS i ON i.id_producto = p.id_producto
        WHERE p.id_comercio = ? AND p.activo = 1 {search_condition}
        ORDER BY {exact_barcode_order}, p.nombre
        LIMIT 50
        """,
        parameters,
    ).fetchall()


def _get_available_pos_product(connection, commerce_id, product_id):
    return connection.execute(
        """
        SELECT
            p.id_producto,
            p.nombre,
            p.precio_venta,
            i.stock_actual
        FROM producto AS p
        JOIN inventario AS i ON i.id_producto = p.id_producto
        WHERE p.id_producto = ? AND p.id_comercio = ? AND p.activo = 1
        """,
        (product_id, commerce_id),
    ).fetchone()


def _load_pos_cart(connection, commerce_id, cart):
    lines = []
    total = Decimal("0.00")
    has_issues = False

    for product_id, quantity in cart.items():
        product = connection.execute(
            """
            SELECT
                p.id_producto,
                p.nombre,
                p.codigo_barras,
                p.precio_venta,
                p.activo,
                i.stock_actual
            FROM producto AS p
            LEFT JOIN inventario AS i ON i.id_producto = p.id_producto
            WHERE p.id_producto = ? AND p.id_comercio = ?
            """,
            (product_id, commerce_id),
        ).fetchone()

        issue = None
        if product is None:
            has_issues = True
            lines.append({
                "id_producto": product_id,
                "nombre": "Producto no disponible",
                "codigo_barras": None,
                "precio_venta": Decimal("0.00"),
                "stock_actual": 0,
                "cantidad": quantity,
                "subtotal": Decimal("0.00"),
                "issue": "El producto ya no está disponible para este comercio.",
            })
            continue

        unit_price = Decimal(str(product["precio_venta"])).quantize(Decimal("0.01"))
        line_subtotal = (unit_price * quantity).quantize(Decimal("0.01"))
        if not product["activo"]:
            issue = "El producto está inactivo. Quitalo del carrito."
        elif product["stock_actual"] is None:
            issue = "El producto no tiene Inventario disponible."
        elif quantity > product["stock_actual"]:
            issue = "La cantidad supera el stock actual. Corregila antes de confirmar."

        if issue:
            has_issues = True
        total += line_subtotal
        lines.append({
            "id_producto": product["id_producto"],
            "nombre": product["nombre"],
            "codigo_barras": product["codigo_barras"],
            "precio_venta": unit_price,
            "stock_actual": product["stock_actual"] or 0,
            "cantidad": quantity,
            "subtotal": line_subtotal,
            "issue": issue,
        })

    return lines, total, has_issues


def _parse_positive_integer(value):
    try:
        if isinstance(value, bool) or "." in str(value):
            return None
        quantity = int(value)
    except (TypeError, ValueError):
        return None
    return quantity if quantity > 0 else None


def _redirect_to_pos():
    search = request.form.get("q", "").strip()
    if search:
        return redirect(url_for("ventas.punto_venta", q=search))
    return redirect(url_for("ventas.punto_venta"))
