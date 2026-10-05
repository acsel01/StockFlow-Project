from flask import Blueprint, render_template

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/dashboard")
def index():
    return render_template("placeholder.html", title="Dashboard")
