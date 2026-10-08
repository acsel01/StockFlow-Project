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

Pull Request #21 mergeado a `develop` mediante el merge commit `db80030`. El Issue #9 fue cerrado como completado y no queda trabajo pendiente para este Issue.

## 2026-10-08 — Issue #10: Implementar módulo de Inventario

### Rama

`feature/inventario`

### Objetivo

Implementar la consulta y modificación controlada del stock, con trazabilidad completa de cada ajuste, permisos diferenciados y aislamiento por comercio.

### Cambios realizados

- Se reemplazó el placeholder por un listado real de Inventario con búsqueda y filtro de stock bajo.
- Se incorporaron los estados derivados `Disponible`, `Pocas unidades` y `Agotado`.
- ADMIN puede modificar stock mínimo y realizar ajustes manuales; VENDEDOR conserva acceso de solo consulta.
- Se implementaron Reposición, Pérdida, Corrección, Conteo físico y Otro con sus reglas específicas.
- Se rechazó explícitamente el uso manual del tipo `VENTA`, reservado para el futuro Punto de Venta.
- Todo cambio de stock actualiza Inventario y crea MovimientoInventario dentro de una única transacción.
- Se agregó un historial administrativo con búsqueda por producto, filtro por tipo y orden descendente.
- Se mantuvieron visibles los Inventarios y movimientos de productos inactivos para preservar trazabilidad.
- Todas las consultas y modificaciones verifican el comercio mediante `g.user["id_comercio"]`.

### Archivos creados o modificados

- `routes/inventario.py`
- `templates/inventario/index.html`
- `templates/inventario/ajustar.html`
- `templates/inventario/movimientos.html`
- `tests/test_inventory.py`
- `docs/DEVLOG.md`

### Funciones o componentes importantes

- `index()`: lista Inventario, busca por producto o código y permite filtrar productos agotados o con pocas unidades.
- `update_minimum_stock()`: valida y actualiza `stock_minimo` sin crear un movimiento de stock.
- `adjust_stock()`: presenta el formulario administrativo y delega el cambio a la función central.
- `movements()`: muestra el historial del comercio actual, con filtros y orden reciente primero.
- `get_availability_status()`: deriva la disponibilidad a partir de `stock_actual` y `stock_minimo`.
- `apply_stock_movement()`: valida, calcula, actualiza Inventario, inserta MovimientoInventario y confirma o revierte toda la transacción.
- `_calculate_delta()`: traduce la cantidad ingresada a `cantidad_delta` según la semántica de cada tipo manual.
- `_get_inventory()` y `_find_inventory()`: recuperan Inventario mediante joins y verifican el comercio actual.

### Decisiones técnicas

- Inventario es la única fuente de verdad para `stock_actual`, `stock_minimo` y `ultima_actualizacion`; Producto conserva solamente la ficha comercial.
- Todo cambio de `stock_actual` crea MovimientoInventario para conservar quién, cuándo, por qué y cómo cambió el valor.
- Cambiar `stock_minimo` no crea MovimientoInventario porque no altera existencias, pero sí actualiza `ultima_actualizacion`.
- `Agotado` corresponde a stock 0; `Pocas unidades` a stock positivo menor o igual al mínimo; `Disponible` a stock mayor al mínimo. El estado no se almacena en una columna.
- `VENTA` no puede seleccionarse manualmente porque será generada automáticamente por el futuro Punto de Venta.
- `id_usuario` se toma de `g.user["id_usuario"]` y `id_comercio` de `g.user["id_comercio"]`; ninguno se acepta desde el formulario.
- La transacción usa `BEGIN IMMEDIATE`, lee el stock actual, calcula y valida el resultado, actualiza Inventario e inserta el movimiento antes del `commit`.
- Si falla el `UPDATE` o el `INSERT` del movimiento, se ejecuta `rollback` y el stock vuelve a su valor anterior.
- `stock_anterior` es el valor antes del ajuste, `cantidad_delta` es la variación con signo y `stock_resultante` es el valor final validado.
- Los productos inactivos conservan Inventario y movimientos; su activación continúa siendo responsabilidad del módulo Productos.
- No se modificó `database/schema.sql` ni se incorporaron columnas derivadas.

### Pruebas realizadas

Se ejecutó la suite completa con:

```text
.venv\Scripts\python -m pytest -q
```

Resultado: `104 passed`.

Las 45 pruebas nuevas cubren permisos, visibilidad por rol, búsquedas, disponibilidad y casos límite, stock mínimo, todos los tipos manuales, prevención de negativos, conteo sin cambios, trazabilidad, productos inactivos, aislamiento entre comercios e historial. También fuerzan un fallo real mediante un trigger SQLite y verifican que el rollback restaure el stock y no deje movimientos parciales.

Se ejecutaron además `python -m compileall` y `git diff --check`, ambos sin errores.

### Problemas encontrados

La rama local `develop` todavía no contenía el merge del Issue #9. Se actualizó mediante `git fetch origin` y `git pull --ff-only origin develop` hasta el merge commit `db80030` antes de crear esta rama. La implementación y las pruebas no presentaron fallos funcionales.

### Resultado

El Issue #10 quedó implementado y probado: ADMIN puede administrar stock con trazabilidad atómica, VENDEDOR puede consultar existencias exactas y ningún usuario accede a Inventario o movimientos de otro comercio.

### Pendiente

Pull Request #22 mergeado a `develop` mediante el merge commit `5287010`. El Issue #10 fue cerrado como completado y no queda trabajo pendiente para este Issue.
