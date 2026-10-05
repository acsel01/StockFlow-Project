import os
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, redirect, url_for

from routes import register_blueprints


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE = BASE_DIR / "database" / "stockflow.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"


def initialize_database(database_path: Path) -> None:
    """Crea las tablas iniciales si todavía no existen."""
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def create_app(test_config=None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("STOCKFLOW_SECRET_KEY", "dev-change-me"),
        DATABASE=os.getenv("STOCKFLOW_DATABASE", str(DEFAULT_DATABASE)),
    )

    if test_config:
        app.config.update(test_config)

    initialize_database(Path(app.config["DATABASE"]))
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
