from datetime import datetime, timezone


LOCAL_DATETIME_FORMAT = "%d/%m/%Y %H:%M"


def format_local_datetime(value):
    """Formatea un timestamp SQLite UTC en la zona local del sistema.

    Los valores vacíos se muestran vacíos. Si el valor no puede interpretarse,
    se conserva su representación original para evitar un error de render y
    mantener visible el dato problemático.
    """
    if value is None or value == "":
        return ""

    if isinstance(value, datetime):
        parsed_value = value
    elif isinstance(value, str):
        try:
            parsed_value = datetime.fromisoformat(value)
        except ValueError:
            return value
    else:
        return str(value)

    if parsed_value.tzinfo is None:
        parsed_value = parsed_value.replace(tzinfo=timezone.utc)

    return parsed_value.astimezone().strftime(LOCAL_DATETIME_FORMAT)
