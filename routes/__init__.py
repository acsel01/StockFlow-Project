from .auth import auth_bp
from .caja import caja_bp
from .catalogo import catalogo_bp
from .dashboard import dashboard_bp
from .estadisticas import estadisticas_bp
from .inventario import inventario_bp
from .productos import productos_bp
from .ventas import ventas_bp


def register_blueprints(app) -> None:
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(productos_bp)
    app.register_blueprint(inventario_bp)
    app.register_blueprint(ventas_bp)
    app.register_blueprint(caja_bp)
    app.register_blueprint(estadisticas_bp)
    app.register_blueprint(catalogo_bp)
