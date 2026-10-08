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

Pull Request #19 mergeado a `develop` mediante el merge commit `8b5bf53`. El Issue #7 fue cerrado como completado y no queda trabajo pendiente para este Issue.

## 2026-10-07 — Issue #8: Implementar autenticación, sesiones y permisos

### Rama

`feature/autenticacion`

### Objetivo

Permitir que administradores y vendedores inicien y cierren sesión de forma segura, y limitar las rutas internas de acuerdo con su rol sin agregar gestión de usuarios ni módulos funcionales.

### Cambios realizados

- Se implementó el formulario de login con búsqueda por email y verificación del hash de contraseña.
- Se agregó una sesión de Flask que guarda únicamente `user_id`.
- Se incorporó la carga del usuario actual en `g.user` antes de cada request.
- Se implementó logout por `POST` y limpieza completa de la sesión.
- Se agregaron decoradores para exigir autenticación o el rol `ADMIN`.
- Se protegieron las rutas internas y se mantuvo `/catalogo` como ruta pública.
- Se creó una plantilla específica de login y un acceso de cierre de sesión en la barra de navegación.
- Se agregaron usuarios ADMIN, VENDEDOR e INACTIVO exclusivamente dentro de fixtures de prueba y con contraseñas hasheadas.

### Archivos creados o modificados

- `routes/auth.py`
- `routes/caja.py`
- `routes/dashboard.py`
- `routes/estadisticas.py`
- `routes/inventario.py`
- `routes/productos.py`
- `routes/ventas.py`
- `templates/base.html`
- `templates/auth/login.html`
- `tests/test_auth.py`
- `docs/DEVLOG.md`

### Funciones o componentes importantes

- `login()`: procesa `GET /login` y `POST /login`, comprueba que el usuario esté activo y valida la contraseña con `check_password_hash()`.
- `logout()`: atiende `POST /logout`, limpia la sesión y redirige al login.
- `load_logged_in_user()`: obtiene `session["user_id"]`, consulta el usuario en SQLite y lo expone como `g.user`; también invalida sesiones de usuarios inexistentes o inactivos.
- `login_required`: redirige a `/login` cuando no existe un usuario autenticado.
- `role_required(role)`: redirige usuarios anónimos y responde `403 Forbidden` cuando el usuario autenticado no tiene el rol requerido.

### Decisiones técnicas

- Se usaron las sesiones firmadas de Flask porque permiten conservar la identidad entre requests sin incorporar una librería externa.
- La sesión guarda solamente `user_id`; no contiene contraseña, hash, rol ni otros datos sensibles. El rol actual se consulta desde la base en cada request.
- Se usó `g.user` para que todas las rutas de un mismo request compartan el usuario cargado sin repetir consultas.
- Las contraseñas se verifican con el hash de Werkzeug y nunca se comparan ni almacenan en texto plano.
- `ADMIN` puede acceder a Productos y Estadísticas; `VENDEDOR` recibe `403` en esas rutas, pero puede usar las rutas operativas protegidas.
- Catálogo sigue público porque el rol CLIENTE no tiene cuenta ni inicia sesión en el MVP.
- La lógica quedó concentrada en `routes/auth.py`; no fue necesario agregar autenticación a `app.py` ni incorporar nuevas dependencias.

### Pruebas realizadas

Se ejecutó la suite completa con:

```text
.venv\Scripts\python -m pytest -q
```

Resultado: `31 passed`.

Las pruebas cubren login correcto de ADMIN y VENDEDOR, contraseña incorrecta, usuario inexistente, usuario inactivo, logout, contenido mínimo de la sesión, acceso anónimo, permisos de ambos roles y acceso público al Catálogo. También se mantuvieron pasando las pruebas del Issue #7 y la prueba de salud.

Se ejecutó además `python -m compileall` sobre la aplicación y las pruebas, sin errores.

### Problemas encontrados

La referencia local de `develop` todavía no contenía el merge del Issue #7. Se ejecutó `git fetch origin`, se creó la rama local `develop` siguiendo `origin/develop` y se verificó con `git pull --ff-only` que quedara actualizada antes de crear esta rama. No hubo fallos funcionales durante la implementación.

### Resultado

El Issue #8 quedó implementado y cubierto por pruebas: los usuarios activos pueden autenticarse, la sesión se reconstruye de forma segura y las rutas aplican la matriz de permisos definida para ADMIN, VENDEDOR y CLIENTE.

### Pendiente

Revisión local, push de `feature/autenticacion` y posterior Pull Request hacia `develop`. No se realizó merge ni se avanzó con otros Issues.
