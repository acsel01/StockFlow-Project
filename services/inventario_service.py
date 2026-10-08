"""Reglas reutilizables de Inventario."""


def get_availability_status(current_stock, minimum_stock):
    """Deriva la disponibilidad actual sin almacenarla en la base."""
    if current_stock == 0:
        return "Agotado"
    if current_stock <= minimum_stock:
        return "Pocas unidades"
    return "Disponible"
