"""Consultas de solo lectura y proyecciones seguras del Catálogo público."""

from services.inventario_service import get_availability_status


def get_public_commerces(connection):
    """Lista únicamente comercios activos y sus datos públicos básicos."""
    return connection.execute(
        """
        SELECT id_comercio, nombre, direccion, barrio, localidad
        FROM comercio
        WHERE activo = 1
        ORDER BY nombre
        """
    ).fetchall()


def get_public_commerce(connection, commerce_id):
    """Obtiene un comercio activo o devuelve None."""
    return connection.execute(
        """
        SELECT id_comercio, nombre, direccion, barrio, localidad
        FROM comercio
        WHERE id_comercio = ? AND activo = 1
        """,
        (commerce_id,),
    ).fetchone()


def get_public_categories(connection, commerce_id):
    """Lista categorías activas que actualmente tienen productos públicos."""
    return connection.execute(
        """
        SELECT DISTINCT c.id_categoria, c.nombre
        FROM producto AS p
        JOIN comercio AS co ON co.id_comercio = p.id_comercio
        JOIN categoria AS c
            ON c.id_categoria = p.id_categoria
            AND c.id_comercio = p.id_comercio
        JOIN inventario AS i ON i.id_producto = p.id_producto
        WHERE
            c.id_comercio = ?
            AND co.activo = 1
            AND c.activa = 1
            AND p.activo = 1
            AND p.visible_catalogo = 1
        ORDER BY c.nombre
        """,
        (commerce_id,),
    ).fetchall()


def get_public_catalog(
    connection,
    commerce_id,
    search="",
    category_id=None,
):
    """Construye una proyección pública sin cantidades ni costos internos."""
    parameters = [commerce_id]
    conditions = []
    if search:
        conditions.append("p.nombre LIKE ?")
        parameters.append(f"%{search}%")
    if category_id is not None:
        conditions.append("c.id_categoria = ?")
        parameters.append(category_id)
    extra_conditions = ""
    if conditions:
        extra_conditions = "AND " + " AND ".join(conditions)

    rows = connection.execute(
        f"""
        SELECT
            p.nombre,
            p.descripcion,
            p.imagen_url,
            CASE
                WHEN p.mostrar_precio_catalogo = 1 THEN p.precio_venta
                ELSE NULL
            END AS public_price,
            c.nombre AS category_name,
            i.stock_actual,
            i.stock_minimo
        FROM producto AS p
        JOIN comercio AS co ON co.id_comercio = p.id_comercio
        JOIN categoria AS c
            ON c.id_categoria = p.id_categoria
            AND c.id_comercio = p.id_comercio
        JOIN inventario AS i ON i.id_producto = p.id_producto
        WHERE
            p.id_comercio = ?
            AND co.activo = 1
            AND p.activo = 1
            AND p.visible_catalogo = 1
            AND c.activa = 1
            {extra_conditions}
        ORDER BY c.nombre, p.nombre
        """,
        parameters,
    ).fetchall()

    return [
        {
            "name": row["nombre"],
            "description": row["descripcion"],
            "image_url": row["imagen_url"],
            "price": row["public_price"],
            "category": row["category_name"],
            "availability": get_availability_status(
                row["stock_actual"],
                row["stock_minimo"],
            ),
        }
        for row in rows
    ]
