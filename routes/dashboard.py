from datetime import date

from flask import Blueprint, g, render_template

from database.db import get_db
from services.estadisticas_service import (
    get_cash_register_sales_summary,
    get_low_stock_products,
    get_sales_summary,
)

from .auth import login_required
from .caja import get_open_cash_register

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/dashboard")
@login_required
def index():
    connection = get_db()
    commerce_id = g.user["id_comercio"]
    open_cash_register = get_open_cash_register(connection, commerce_id)
    low_stock_products = get_low_stock_products(connection, commerce_id)
    admin_summary = None
    cash_register_summary = None

    if g.user["rol"] == "ADMIN":
        today = date.today()
        admin_summary = get_sales_summary(
            connection,
            commerce_id,
            today,
            today,
        )
    elif open_cash_register is not None:
        cash_register_summary = get_cash_register_sales_summary(
            connection,
            commerce_id,
            open_cash_register["id_caja"],
        )

    return render_template(
        "dashboard/index.html",
        open_cash_register=open_cash_register,
        admin_summary=admin_summary,
        cash_register_summary=cash_register_summary,
        low_stock_count=len(low_stock_products),
        low_stock_products=low_stock_products[:5],
    )
