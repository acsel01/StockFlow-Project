import os
from pathlib import Path

from flask import Flask, jsonify, redirect, url_for

from database.db import close_db, init_db
from routes import register_blueprints
from utils.datetime_utils import format_local_datetime


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE = BASE_DIR / "database" / "stockflow.db"


def create_app(test_config=None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("STOCKFLOW_SECRET_KEY", "dev-change-me"),
        DATABASE=os.getenv("STOCKFLOW_DATABASE", str(DEFAULT_DATABASE)),
    )

    if test_config:
        app.config.update(test_config)

    app.jinja_env.filters["local_datetime"] = format_local_datetime
    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    register_blueprints(app)

    @app.get("/")
    def index():
        return redirect(url_for("catalogo.index"))

    @app.get("/health")
    def health():
        return jsonify(status="ok", application="StockFlow")

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
