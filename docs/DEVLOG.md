# Registro de desarrollo

## 2026-10-07 — Issue #7: Implementar base de datos SQLite y acceso a datos

### Rama

`feature/base-datos-sqlite`

### Objetivo

Centralizar el acceso a SQLite y permitir que StockFlow cree desde cero las nueve tablas aprobadas, sin incorporar un ORM ni datos funcionales.

### Cambios realizados

- Se trasladó la apertura e inicialización de SQLite desde `app.py` a `database/db.py`.
- Se integró el cierre automático de la conexión con el contexto de Flask.
- Se mantuvo la inicialización automática desde `database/schema.sql` al crear la aplicación.
- Se agregaron pruebas aisladas con una base temporal.
- Se verificó que `.gitignore` ya excluye archivos `.db`, `.sqlite` y `.sqlite3` dentro de `database/`; no fue necesario modificarlo.

### Archivos creados o modificados

- `app.py`
- `database/__init__.py`
- `database/db.py`
- `tests/test_database.py`
- `docs/DEVLOG.md`

### Funciones o componentes importantes

- `get_db()`: abre una conexión solo cuando el contexto actual la necesita, la guarda en `flask.g` para reutilizarla, configura `sqlite3.Row` y activa `PRAGMA foreign_keys = ON`.
- `close_db()`: retira la conexión de `flask.g` y la cierra si existe; también es seguro llamarla cuando no hay una conexión abierta.
- `init_db()`: obtiene la conexión compartida y ejecuta el contenido de `database/schema.sql`.
- `create_app()`: registra `close_db()` como función de cierre e invoca `init_db()` dentro de un contexto de aplicación.

### Decisiones técnicas

- Se utilizó el módulo `sqlite3` incluido en Python, sin ORM ni dependencias nuevas, para conservar una solución directa y fácil de explicar.
- Se eligió `flask.g` porque su duración coincide con la solicitud o contexto actual y evita conexiones repetidas.
- Se utilizó `sqlite3.Row` para permitir acceso a los resultados por nombre de columna además de por posición.
- Las claves foráneas se habilitan al crear cada conexión, porque SQLite requiere activar esta opción por conexión.
- No se modificó `database/schema.sql`: ya define exactamente nueve tablas, conserva un único `precio_venta` y contiene las banderas independientes `visible_catalogo` y `mostrar_precio_catalogo`.
- No se agregaron datos de desarrollo ni lógica de otros Issues.

### Pruebas realizadas

Se ejecutó la suite completa con:

```text
.venv\Scripts\python -m pytest -q
```

Resultado: `7 passed`.

Las pruebas comprueban la ruta de salud existente, la creación exacta de las nueve tablas, la activación de claves foráneas, el rechazo de una relación inválida, la presencia de las dos banderas de catálogo, el uso y reutilización de una conexión con `sqlite3.Row`, y el cierre seguro de la conexión.

También se compiló el código Python con `python -m compileall` sin errores.

### Problemas encontrados

El entorno no tenía `pytest` disponible. Se creó el entorno virtual local `.venv`, ignorado por Git, y se instalaron las dependencias declaradas en `requirements.txt`. Después de eso, todas las pruebas finalizaron correctamente.

### Resultado

La capa de acceso SQLite del Issue #7 quedó implementada, integrada y cubierta por pruebas. La aplicación puede inicializar una base vacía con las nueve tablas y administrar una conexión por contexto de Flask.

### Pendiente

Pull Request #19 abierto hacia `develop`, revisado y pendiente de merge. No se avanzó con otros Issues.
