from flask import Blueprint, render_template

auth_bp = Blueprint("auth", __name__)


@auth_bp.get("/login")
def login():
    return render_template("placeholder.html", title="Inicio de sesión")
