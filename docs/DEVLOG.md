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

Pull Request #20 mergeado a `develop` mediante el merge commit `440ee0f`. El Issue #8 fue cerrado como completado y no queda trabajo pendiente para este Issue.

## 2026-10-08 — Issue #9: Implementar gestión de Productos

### Rama

`feature/productos`

### Objetivo

Implementar el primer CRUD funcional de StockFlow para que el rol ADMIN pueda administrar Productos y Categorías de su propio comercio, manteniendo separada la responsabilidad de Inventario.

### Cambios realizados

- Se reemplazó el placeholder de Productos por un listado con búsqueda por nombre o código de barras.
- Se implementaron alta y edición de la ficha comercial del producto con validaciones de backend.
- La creación inserta Producto e Inventario inicial en una única transacción.
- Se agregaron baja lógica y reactivación de productos, sin eliminar registros.
- Se implementó la gestión básica de Categorías: listado, alta, desactivación y reactivación.
- Se incorporó `id_comercio` a `g.user` y se filtraron todas las consultas y modificaciones con ese valor.
- Se mantuvo `session` con solamente `user_id`; el comercio no se recibe desde formularios ni se guarda en sesión.
- Se agregaron plantillas específicas para listado, formulario y categorías, además de mensajes `flash` en la plantilla base.
- Se mantuvieron independientes las opciones `visible_catalogo` y `mostrar_precio_catalogo`.

### Archivos creados o modificados

- `routes/auth.py`
- `routes/productos.py`
- `templates/base.html`
- `templates/productos/index.html`
- `templates/productos/form.html`
- `templates/productos/categorias.html`
- `tests/test_products.py`
- `docs/DEVLOG.md`

### Funciones o componentes importantes

- `index()`: lista y busca productos del comercio del ADMIN autenticado.
- `create_product()`: valida la ficha, inserta Producto, crea Inventario en cero y confirma ambas operaciones juntas.
- `edit_product()`: modifica únicamente los datos comerciales de un producto del comercio actual.
- `deactivate_product()` y `activate_product()`: aplican baja lógica y reactivación.
- `categories()`: lista y crea categorías del comercio.
- `deactivate_category()` y `activate_category()`: cambian el estado sin borrar la categoría ni sus productos.
- `_validate_product_form()`: valida nombre, categoría, precios y unicidad del código de barras.
- `_get_product()`: obtiene el producto por identificador y comercio, o responde 404.

### Decisiones técnicas

- Producto conserva la ficha comercial e Inventario conserva stock y movimientos; por eso los formularios de Producto no leen ni modifican cantidades.
- Cada Producto nuevo recibe una fila de Inventario con `stock_actual = 0` y `stock_minimo = 0` para mantener la relación uno a uno desde su creación.
- Producto e Inventario se insertan en la misma transacción y solo se ejecuta `commit` después de ambas operaciones; cualquier error provoca `rollback`.
- Se usa baja lógica para conservar la ficha, su Inventario y el historial que pueda asociarse en Issues posteriores.
- Los precios se validan con `Decimal` en el backend porque las restricciones HTML pueden omitirse o manipularse.
- Un código de barras vacío se convierte en `NULL`, permitiendo varios productos sin código sin romper la restricción de unicidad.
- Todas las consultas usan `g.user["id_comercio"]`; no se confía en un comercio enviado por el navegador y los registros ajenos responden 404.
- `visible_catalogo` decide si el producto puede publicarse; `mostrar_precio_catalogo` configura si se mostrará el mismo `precio_venta`. No existe un precio público separado y ambas banderas se almacenan de forma independiente.
- Las categorías inactivas se conservan en productos históricos, pero solo categorías activas pueden seleccionarse en altas o ediciones.

### Pruebas realizadas

Se ejecutó la suite completa con:

```text
.venv\Scripts\python -m pytest -q
```

Resultado: `59 passed`.

Las 28 pruebas nuevas cubren permisos, listado, búsquedas, creación, Inventario inicial, rollback atómico, validación de precios y categorías, códigos duplicados o nulos, edición, baja lógica, reactivación, banderas de Catálogo, Categorías y aislamiento entre dos comercios. Se mantuvieron pasando los 31 tests anteriores.

También se ejecutó `python -m compileall` sobre la aplicación y las pruebas, sin errores.

### Problemas encontrados

La rama local `develop` todavía no contenía el merge del Issue #8. Se actualizó mediante `git fetch origin` y `git pull --ff-only origin develop` hasta el merge commit `440ee0f` antes de crear esta rama. La implementación y las pruebas no presentaron fallos funcionales.

### Resultado

El Issue #9 quedó implementado y probado: ADMIN puede gestionar Productos y Categorías de su comercio, VENDEDOR continúa recibiendo 403 y ninguna operación de este módulo modifica stock.

### Pendiente

Pull Request #21 abierto desde `feature/productos` hacia `develop`, revisado y pendiente de merge. No se avanzó con el Issue #10.
