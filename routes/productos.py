import sqlite3
from decimal import Decimal, InvalidOperation

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

from .auth import role_required

productos_bp = Blueprint("productos", __name__)


@productos_bp.get("/productos")
@role_required("ADMIN")
def index():
    search = request.args.get("q", "").strip()
    parameters = [g.user["id_comercio"]]
    search_condition = ""

    if search:
        search_condition = "AND (p.nombre LIKE ? OR p.codigo_barras LIKE ?)"
        search_value = f"%{search}%"
        parameters.extend((search_value, search_value))

    products = get_db().execute(
        f"""
        SELECT
            p.id_producto,
            p.nombre,
            p.codigo_barras,
            p.precio_compra,
            p.precio_venta,
            p.activo,
            p.visible_catalogo,
            p.mostrar_precio_catalogo,
            c.nombre AS categoria_nombre
        FROM producto AS p
        JOIN categoria AS c ON c.id_categoria = p.id_categoria
        WHERE p.id_comercio = ? {search_condition}
        ORDER BY p.nombre
        """,
        parameters,
    ).fetchall()

    return render_template(
        "productos/index.html",
        products=products,
        search=search,
    )


@productos_bp.route("/productos/nuevo", methods=("GET", "POST"))
@role_required("ADMIN")
def create_product():
    categories = _get_categories()
    form = _empty_product_form()
    error = None

    if request.method == "POST":
        form = _read_product_form()
        error, category_id, purchase_price, sale_price = _validate_product_form(form)

        if error is None:
            connection = get_db()

            try:
                product = connection.execute(
                    """
                    INSERT INTO producto (
                        id_comercio,
                        id_categoria,
                        nombre,
                        descripcion,
                        codigo_barras,
                        precio_compra,
                        precio_venta,
                        imagen_url,
                        visible_catalogo,
                        mostrar_precio_catalogo,
                        activo
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        g.user["id_comercio"],
                        category_id,
                        form["nombre"],
                        form["descripcion"],
                        form["codigo_barras"],
                        purchase_price,
                        sale_price,
                        form["imagen_url"],
                        form["visible_catalogo"],
                        form["mostrar_precio_catalogo"],
                        form["activo"],
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO inventario (
                        id_producto, stock_actual, stock_minimo
                    ) VALUES (?, 0, 0)
                    """,
                    (product.lastrowid,),
                )
                connection.commit()
            except sqlite3.IntegrityError:
                connection.rollback()
                error = "No se pudo crear el producto. Revisá el código de barras."
            else:
                flash("Producto creado correctamente.", "success")
                return redirect(url_for("productos.index"))

    return render_template(
        "productos/form.html",
        title="Nuevo producto",
        submit_label="Crear producto",
        form=form,
        categories=categories,
        error=error,
    )


@productos_bp.route(
    "/productos/<int:product_id>/editar",
    methods=("GET", "POST"),
)
@role_required("ADMIN")
def edit_product(product_id):
    product = _get_product(product_id)
    categories = _get_categories(product["id_categoria"])
    form = _product_to_form(product)
    error = None

    if request.method == "POST":
        form = _read_product_form()
        error, category_id, purchase_price, sale_price = _validate_product_form(
            form,
            product_id,
        )

        if error is None:
            connection = get_db()

            try:
                connection.execute(
                    """
                    UPDATE producto
                    SET
                        id_categoria = ?,
                        nombre = ?,
                        descripcion = ?,
                        codigo_barras = ?,
                        precio_compra = ?,
                        precio_venta = ?,
                        imagen_url = ?,
                        visible_catalogo = ?,
                        mostrar_precio_catalogo = ?,
                        activo = ?
                    WHERE id_producto = ? AND id_comercio = ?
                    """,
                    (
                        category_id,
                        form["nombre"],
                        form["descripcion"],
                        form["codigo_barras"],
                        purchase_price,
                        sale_price,
                        form["imagen_url"],
                        form["visible_catalogo"],
                        form["mostrar_precio_catalogo"],
                        form["activo"],
                        product_id,
                        g.user["id_comercio"],
                    ),
                )
                connection.commit()
            except sqlite3.IntegrityError:
                connection.rollback()
                error = "No se pudo actualizar el producto. Revisá el código de barras."
            else:
                flash("Producto actualizado correctamente.", "success")
                return redirect(url_for("productos.index"))

    return render_template(
        "productos/form.html",
        title="Editar producto",
        submit_label="Guardar cambios",
        form=form,
        categories=categories,
        error=error,
    )


@productos_bp.post("/productos/<int:product_id>/desactivar")
@role_required("ADMIN")
def deactivate_product(product_id):
    _set_product_active(product_id, False)
    flash("Producto desactivado correctamente.", "success")
    return redirect(url_for("productos.index"))


@productos_bp.post("/productos/<int:product_id>/activar")
@role_required("ADMIN")
def activate_product(product_id):
    _set_product_active(product_id, True)
    flash("Producto activado correctamente.", "success")
    return redirect(url_for("productos.index"))


@productos_bp.route("/categorias", methods=("GET", "POST"))
@role_required("ADMIN")
def categories():
    error = None
    name = ""
    description = ""

    if request.method == "POST":
        name = request.form.get("nombre", "").strip()
        description = request.form.get("descripcion", "").strip()

        if not name:
            error = "El nombre de la categoría es obligatorio."
        elif get_db().execute(
            """
            SELECT 1
            FROM categoria
            WHERE id_comercio = ? AND lower(nombre) = lower(?)
            """,
            (g.user["id_comercio"], name),
        ).fetchone():
            error = "Ya existe una categoría con ese nombre."
        else:
            try:
                connection = get_db()
                connection.execute(
                    """
                    INSERT INTO categoria (
                        id_comercio, nombre, descripcion, activa
                    ) VALUES (?, ?, ?, 1)
                    """,
                    (g.user["id_comercio"], name, description or None),
                )
                connection.commit()
            except sqlite3.IntegrityError:
                connection.rollback()
                error = "No se pudo crear la categoría porque el nombre ya existe."
            else:
                flash("Categoría creada correctamente.", "success")
                return redirect(url_for("productos.categories"))

    category_rows = get_db().execute(
        """
        SELECT
            c.id_categoria,
            c.nombre,
            c.descripcion,
            c.activa,
            COUNT(p.id_producto) AS cantidad_productos
        FROM categoria AS c
        LEFT JOIN producto AS p ON p.id_categoria = c.id_categoria
        WHERE c.id_comercio = ?
        GROUP BY c.id_categoria
        ORDER BY c.nombre
        """,
        (g.user["id_comercio"],),
    ).fetchall()

    return render_template(
        "productos/categorias.html",
        categories=category_rows,
        error=error,
        name=name,
        description=description,
    )


@productos_bp.post("/categorias/<int:category_id>/desactivar")
@role_required("ADMIN")
def deactivate_category(category_id):
    _set_category_active(category_id, False)
    flash("Categoría desactivada correctamente.", "success")
    return redirect(url_for("productos.categories"))


@productos_bp.post("/categorias/<int:category_id>/activar")
@role_required("ADMIN")
def activate_category(category_id):
    _set_category_active(category_id, True)
    flash("Categoría activada correctamente.", "success")
    return redirect(url_for("productos.categories"))


def _get_categories(current_category_id=None):
    parameters = [g.user["id_comercio"]]
    current_condition = ""

    if current_category_id is not None:
        current_condition = "OR id_categoria = ?"
        parameters.append(current_category_id)

    return get_db().execute(
        f"""
        SELECT id_categoria, nombre, activa
        FROM categoria
        WHERE id_comercio = ? AND (activa = 1 {current_condition})
        ORDER BY nombre
        """,
        parameters,
    ).fetchall()


def _get_product(product_id):
    product = get_db().execute(
        """
        SELECT *
        FROM producto
        WHERE id_producto = ? AND id_comercio = ?
        """,
        (product_id, g.user["id_comercio"]),
    ).fetchone()

    if product is None:
        abort(404)

    return product


def _empty_product_form():
    return {
        "nombre": "",
        "descripcion": "",
        "id_categoria": "",
        "codigo_barras": "",
        "precio_compra": "0",
        "precio_venta": "",
        "imagen_url": "",
        "visible_catalogo": False,
        "mostrar_precio_catalogo": False,
        "activo": True,
    }


def _product_to_form(product):
    return {
        "nombre": product["nombre"],
        "descripcion": product["descripcion"] or "",
        "id_categoria": product["id_categoria"],
        "codigo_barras": product["codigo_barras"] or "",
        "precio_compra": product["precio_compra"],
        "precio_venta": product["precio_venta"],
        "imagen_url": product["imagen_url"] or "",
        "visible_catalogo": bool(product["visible_catalogo"]),
        "mostrar_precio_catalogo": bool(product["mostrar_precio_catalogo"]),
        "activo": bool(product["activo"]),
    }


def _read_product_form():
    return {
        "nombre": request.form.get("nombre", "").strip(),
        "descripcion": request.form.get("descripcion", "").strip() or None,
        "id_categoria": request.form.get("id_categoria", "").strip(),
        "codigo_barras": request.form.get("codigo_barras", "").strip() or None,
        "precio_compra": request.form.get("precio_compra", "").strip(),
        "precio_venta": request.form.get("precio_venta", "").strip(),
        "imagen_url": request.form.get("imagen_url", "").strip() or None,
        "visible_catalogo": "visible_catalogo" in request.form,
        "mostrar_precio_catalogo": "mostrar_precio_catalogo" in request.form,
        "activo": "activo" in request.form,
    }


def _validate_product_form(form, product_id=None):
    if not form["nombre"]:
        return "El nombre es obligatorio.", None, None, None

    try:
        category_id = int(form["id_categoria"])
    except (TypeError, ValueError):
        return "Seleccioná una categoría válida.", None, None, None

    category = get_db().execute(
        """
        SELECT 1
        FROM categoria
        WHERE id_categoria = ? AND id_comercio = ? AND activa = 1
        """,
        (category_id, g.user["id_comercio"]),
    ).fetchone()

    if category is None:
        return "Seleccioná una categoría activa de tu comercio.", None, None, None

    purchase_price = _parse_price(form["precio_compra"])
    if purchase_price is None:
        return "Ingresá un precio de compra válido y mayor o igual a 0.", None, None, None

    sale_price = _parse_price(form["precio_venta"])
    if sale_price is None:
        return "Ingresá un precio de venta válido y mayor o igual a 0.", None, None, None

    if form["codigo_barras"]:
        parameters = [g.user["id_comercio"], form["codigo_barras"]]
        current_product_condition = ""

        if product_id is not None:
            current_product_condition = "AND id_producto != ?"
            parameters.append(product_id)

        duplicate = get_db().execute(
            f"""
            SELECT 1
            FROM producto
            WHERE id_comercio = ? AND codigo_barras = ?
            {current_product_condition}
            """,
            parameters,
        ).fetchone()

        if duplicate:
            return "Ya existe un producto con ese código de barras.", None, None, None

    return None, category_id, purchase_price, sale_price


def _parse_price(value):
    try:
        price = Decimal(value)
    except (InvalidOperation, TypeError):
        return None

    if not price.is_finite() or price < 0:
        return None

    return format(price, "f")


def _set_product_active(product_id, active):
    connection = get_db()
    result = connection.execute(
        """
        UPDATE producto
        SET activo = ?
        WHERE id_producto = ? AND id_comercio = ?
        """,
        (int(active), product_id, g.user["id_comercio"]),
    )

    if result.rowcount == 0:
        connection.rollback()
        abort(404)

    connection.commit()


def _set_category_active(category_id, active):
    connection = get_db()
    result = connection.execute(
        """
        UPDATE categoria
        SET activa = ?
        WHERE id_categoria = ? AND id_comercio = ?
        """,
        (int(active), category_id, g.user["id_comercio"]),
    )

    if result.rowcount == 0:
        connection.rollback()
        abort(404)

    connection.commit()
