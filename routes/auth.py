from functools import wraps

from flask import (
    Blueprint,
    abort,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from database.db import get_db

auth_bp = Blueprint("auth", __name__)


@auth_bp.before_app_request
def load_logged_in_user() -> None:
    """Carga en g.user al usuario identificado por la sesión actual."""
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
        return

    g.user = get_db().execute(
        """
        SELECT id_usuario, nombre, apellido, email, rol, activo
        FROM usuario
        WHERE id_usuario = ?
        """,
        (user_id,),
    ).fetchone()

    if g.user is None or not g.user["activo"]:
        session.clear()
        g.user = None


@auth_bp.route("/login", methods=("GET", "POST"))
def login():
    error = None

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute(
            """
            SELECT id_usuario, password_hash, activo
            FROM usuario
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

        if (
            user is None
            or not user["activo"]
            or not check_password_hash(user["password_hash"], password)
        ):
            error = "Email o contraseña incorrectos."
        else:
            session.clear()
            session["user_id"] = user["id_usuario"]
            return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html", error=error)


@auth_bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


def login_required(view):
    """Redirige al login cuando no hay un usuario autenticado."""
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))

        return view(**kwargs)

    return wrapped_view


def role_required(role):
    """Permite el acceso solo al rol indicado."""
    def decorator(view):
        @wraps(view)
        def wrapped_view(**kwargs):
            if g.user is None:
                return redirect(url_for("auth.login"))

            if g.user["rol"] != role:
                abort(403)

            return view(**kwargs)

        return wrapped_view

    return decorator
