from flask import Blueprint, flash, g, render_template, request

from database.db import get_db
from services.estadisticas_service import (
    get_daily_sales,
    get_estimated_profit,
    get_low_stock_products,
    get_sales_summary,
    get_top_profitable_products,
    get_top_selling_products,
    resolve_period,
)

from .auth import role_required

estadisticas_bp = Blueprint("estadisticas", __name__)


@estadisticas_bp.get("/estadisticas")
@role_required("ADMIN")
def index():
    try:
        period = resolve_period(
            request.args.get("periodo", "30d"),
            request.args.get("desde"),
            request.args.get("hasta"),
        )
    except ValueError as error:
        flash(f"{error} Se muestran los últimos 30 días.", "warning")
        period = resolve_period("30d")

    connection = get_db()
    commerce_id = g.user["id_comercio"]
    date_from = period["date_from"]
    date_to = period["date_to"]
    summary = get_sales_summary(connection, commerce_id, date_from, date_to)
    daily_sales = get_daily_sales(connection, commerce_id, date_from, date_to)
    top_selling_products = get_top_selling_products(
        connection,
        commerce_id,
        date_from,
        date_to,
    )
    estimated_profit = get_estimated_profit(
        connection,
        commerce_id,
        date_from,
        date_to,
    )
    top_profitable_products = get_top_profitable_products(
        connection,
        commerce_id,
        date_from,
        date_to,
    )
    low_stock_products = get_low_stock_products(connection, commerce_id)
    chart_data = {
        "daily_sales": {
            "labels": [row["sale_date"] for row in daily_sales],
            "values": [str(row["total_sold"]) for row in daily_sales],
        },
        "top_products": {
            "labels": [row["product_name"] for row in top_selling_products],
            "values": [row["units_sold"] for row in top_selling_products],
        },
    }

    return render_template(
        "estadisticas/index.html",
        period=period,
        summary=summary,
        daily_sales=daily_sales,
        top_selling_products=top_selling_products,
        estimated_profit=estimated_profit,
        top_profitable_products=top_profitable_products,
        low_stock_products=low_stock_products,
        chart_data=chart_data,
    )
