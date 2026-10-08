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

## 2026-10-08 — Issue #12: Implementar módulo de Caja

### Rama

`feature/caja`

### Objetivo

Implementar la apertura, consulta y cierre de Caja para ADMIN y VENDEDOR, con aislamiento por comercio, resumen derivado de ventas completadas y operaciones transaccionales seguras.

### Cambios realizados

- Se reemplazó el placeholder de Caja por una pantalla real para apertura, seguimiento y cierre.
- ADMIN y VENDEDOR pueden consultar Caja, abrirla con un monto inicial y cerrarla con el efectivo contado.
- Se incorporó un resumen con cantidad de ventas, total vendido, totales por medio de pago y efectivo esperado.
- Se muestra el último cierre con efectivo esperado, efectivo contado y diferencia derivada como cierre exacto, sobrante o faltante.
- Se muestran los usuarios de apertura y cierre mediante joins con Usuario.
- Todas las operaciones se aíslan mediante `g.user["id_comercio"]`; el comercio nunca se recibe desde el navegador.
- La apertura y el cierre usan transacciones con bloqueo temprano y rollback ante errores de SQLite.
- No se modificó el esquema ni se implementaron ventas, Punto de Venta o movimientos de Inventario.

### Archivos creados o modificados

- `routes/caja.py`
- `templates/caja/index.html`
- `tests/test_cash_register.py`
- `docs/DEVLOG.md`

### Funciones o componentes importantes

- `index()`: obtiene la Caja del comercio actual y presenta su resumen o el formulario de apertura.
- `open_cash_register()`: valida el monto inicial, bloquea escrituras con `BEGIN IMMEDIATE`, vuelve a comprobar que no haya otra Caja abierta e inserta la apertura.
- `close_cash_register()`: valida el efectivo contado, relee la Caja abierta dentro de la transacción y registra usuario, fecha y monto de cierre.
- `get_open_cash_register()`: consulta reutilizable para obtener la Caja abierta de un comercio; queda disponible para el futuro módulo de Ventas.
- `get_cash_summary()`: deriva los totales de ventas completadas, el efectivo esperado y la diferencia de cierre.
- `_get_last_closed_cash_register()`: recupera el último cierre del comercio con los datos de los usuarios responsables.
- `_parse_non_negative_amount()`: valida montos finitos y mayores o iguales a cero mediante `Decimal`.

### Decisiones técnicas

- Caja representa una jornada operativa del comercio a la que las futuras ventas quedarán vinculadas. Solo puede existir una `ABIERTA` por comercio para que cada venta tenga una jornada activa inequívoca.
- No se agregó ninguna columna ni tabla porque el esquema actual ya contiene toda la información necesaria en Caja y Venta.
- `monto_inicial` es el efectivo declarado al abrir, `efectivo_esperado` es el inicial más las ventas en efectivo y `efectivo_contado` es el valor físico declarado al cerrar.
- El efectivo esperado se calcula como `monto_inicial + SUM(venta.total)` exclusivamente para ventas completadas en efectivo.
- `dinero_recibido` y `vuelto` no participan del arqueo; tampoco se suman débito, crédito o transferencia al efectivo esperado.
- Los totales por medio de pago, el efectivo esperado y la diferencia se derivan en cada consulta y no se persisten.
- La diferencia se calcula como `efectivo_contado - efectivo_esperado`: cero es cierre exacto, un valor positivo es sobrante y uno negativo es faltante.
- `BEGIN IMMEDIATE` serializa aperturas concurrentes: después de adquirir el bloqueo cada solicitud vuelve a consultar la Caja abierta antes de insertar.
- El cierre actualiza solamente una Caja `ABIERTA` del comercio autenticado y verifica que exactamente una fila haya cambiado.
- Una Caja cerrada no se vuelve a modificar; una apertura posterior crea un registro nuevo.
- Los identificadores de comercio y usuario provienen exclusivamente de `g.user`; así se determina la Caja activa y se evita consultar o cerrar la de otro comercio.
- Los usuarios de apertura y cierre se registran mediante sus identificadores y sus nombres se obtienen con joins, sin duplicarlos en Caja.

### Pruebas realizadas

Se ejecutó la suite completa con:

```text
.venv\Scripts\python.exe -m pytest -q
```

Resultado: `136 passed`.

Las 32 pruebas nuevas cubren autenticación, permisos de ADMIN y VENDEDOR, validaciones, campos de apertura y cierre, una sola Caja abierta por comercio, aperturas independientes entre comercios, aislamiento de consulta y cierre, totales por medio de pago, uso de `venta.total`, efectivo esperado, inmutabilidad, diferencias exacta/positiva/negativa y reutilización de la consulta de Caja abierta. También ejecutan dos aperturas concurrentes y fuerzan fallos reales mediante triggers SQLite para verificar rollback en apertura y cierre.

Se ejecutó además `.venv\Scripts\python.exe -m compileall -q app.py database routes services tests utils`, sin errores.

### Problemas encontrados

La rama local `develop` todavía no contenía el merge del Issue #10. Se actualizó con `git fetch origin` y `git pull --ff-only origin develop` hasta el merge commit `5287010` antes de crear esta rama. El primer intento de ejecutar las pruebas usó el Python global, que no tenía `pytest`; se repitió con el intérprete de `.venv` y la suite completa pasó.

### Resultado

El Issue #12 quedó implementado y probado: ambos roles internos pueden gestionar la Caja de su comercio, los importes se derivan de las ventas completadas correctas y las transacciones evitan aperturas duplicadas o estados parciales ante errores.

### Pendiente

Pull Request #23 mergeado a `develop` mediante el merge commit `fce8528`. El Issue #12 fue cerrado como completado y no queda trabajo pendiente para este Issue.

## 2026-10-08 — Issue #13: Implementar registro e historial de Ventas

### Rama

`feature/ventas`

### Objetivo

Implementar el núcleo transaccional que confirma una Venta completa y permitir que ADMIN y VENDEDOR consulten su historial y detalle, sin implementar todavía la interfaz del Punto de Venta.

### Cambios realizados

- Se reemplazó el `NotImplementedError` de `confirmar_venta()` por el servicio real de confirmación.
- Se validan dentro de una única transacción el usuario, la Caja, los productos, el comercio, el estado activo, las cantidades, el stock, los precios y el medio de pago.
- Los productos repetidos en el carrito se normalizan en una sola línea antes de validar existencias.
- Se calculan con `Decimal` los subtotales, el total y el vuelto a partir de precios releídos desde Producto.
- Se crean Venta y DetalleVenta, se descuenta Inventario y se registra un MovimientoInventario `VENTA` por cada producto.
- Se implementó un historial de ventas con filtro opcional por medio de pago y orden reciente primero.
- Se agregó el detalle histórico con vendedor, Caja, pago, importes, observaciones y productos vendidos.
- El historial y el detalle se aíslan por el comercio de `g.user`; una venta ajena responde 404.
- El Punto de Venta permanece como placeholder y no se agregó ningún endpoint provisional para confirmar ventas.
- No se modificó `database/schema.sql` ni se implementaron carrito, anulación o cancelación.

### Archivos creados o modificados

- `services/venta_service.py`
- `routes/ventas.py`
- `templates/ventas/index.html`
- `templates/ventas/detalle.html`
- `tests/test_sales.py`
- `docs/DEVLOG.md`

### Funciones o componentes importantes

- `confirmar_venta()`: posee la transacción completa y confirma Venta, detalles, cambios de stock y movimientos como una unidad atómica.
- `VentaError`: comunica errores funcionales comprensibles al futuro consumidor del servicio sin depender de Flask.
- `_get_active_user()`: verifica que el usuario exista, esté activo y aporta su comercio persistido.
- `_get_valid_cash_register()`: vuelve a comprobar que la Caja exista, siga abierta y pertenezca al comercio del usuario.
- `_normalize_items()`: valida identificadores y cantidades enteras positivas y combina productos duplicados.
- `_load_sale_lines()`: relee Producto e Inventario, valida comercio, actividad y stock, y calcula importes desde el precio real.
- `_validate_payment()` y `_money()`: validan efectivo, calculan vuelto y normalizan dinero a dos decimales.
- `historial()`: lista ventas del comercio actual con cantidades de productos y unidades.
- `detail()`: obtiene una venta aislada por comercio y muestra sus líneas con precios históricos.

### Decisiones técnicas

- Venta representa la cabecera comercial y de pago; DetalleVenta conserva cada producto, cantidad, precio unitario y subtotal histórico.
- `confirmar_venta()` es dueño de una única transacción porque Venta, detalles, Inventario y movimientos deben confirmarse juntos o revertirse por completo.
- La transacción comienza con `BEGIN IMMEDIATE` para adquirir el bloqueo de escritura antes de releer Caja y existencias, serializando ventas concurrentes en SQLite.
- Caja se relee al confirmar porque podría haberse cerrado mientras se preparaba el futuro carrito.
- Stock también se relee después del bloqueo; así dos ventas no pueden consumir simultáneamente las mismas unidades ni dejar existencias negativas.
- El navegador solo aportará identificadores y cantidades. Precio, subtotal y total se obtienen o calculan en backend y cualquier importe incluido en `items` se ignora.
- DetalleVenta guarda `precio_unitario` porque una edición posterior del precio del Producto no debe alterar una venta histórica.
- No se llama a `apply_stock_movement()` porque esa función administra una transacción propia para ajustes manuales. La Venta necesita controlar una sola transacción global sin commits intermedios.
- Cada MovimientoInventario tiene tipo `VENTA`, delta negativo e `id_venta` no nulo para rastrear exactamente qué operación produjo la salida.
- El comercio se deriva primero del usuario persistido y se compara con Caja y Producto; nunca se acepta `id_comercio` desde el cliente.
- Para efectivo, `dinero_recibido` es obligatorio y el vuelto se calcula como recibido menos total. Para débito, crédito y transferencia ambos campos se guardan en `NULL`, aunque el cliente envíe valores.
- No se implementó anulación posterior porque el esquema actual solo admite ventas `COMPLETADA` y ese comportamiento está fuera del alcance del Issue.
- El historial usa joins operativos, pero nunca expone precio de compra, costos, márgenes o ganancias a VENDEDOR.

### Pruebas realizadas

Se ejecutó la suite completa con:

```text
.venv\Scripts\python.exe -m pytest -q
```

Resultado: `181 passed`.

Las 45 pruebas nuevas cubren ventas simples y múltiples, productos duplicados, carrito vacío, cantidades inválidas, productos inexistentes, ajenos o inactivos, stock insuficiente, usuarios y Cajas inválidos, Caja cerrada antes de confirmar, precio vigente del backend, precio histórico, todos los medios de pago, efectivo insuficiente, vuelto, importes no efectivos en `NULL`, descuento cero, actualización de Inventario y trazabilidad completa del movimiento. También fuerzan un error real al insertar MovimientoInventario y comprueban rollback total, además de ejecutar dos ventas concurrentes por el mismo stock y verificar que no exista sobreventa.

Las pruebas de interfaz cubren permisos, orden, filtro, aislamiento entre comercios, detalle histórico, ausencia de información económica sensible para VENDEDOR y permanencia del Punto de Venta como placeholder. Los 136 tests anteriores continúan pasando.

Se ejecutó además `.venv\Scripts\python.exe -m compileall -q app.py database routes services tests utils`, sin errores.

### Problemas encontrados

La rama local `develop` estaba detrás del merge del Issue #12. Se actualizó mediante `git fetch origin` y `git pull --ff-only origin develop` hasta `fce8528` antes de crear `feature/ventas`. Durante las pruebas, una aserción esperaba un texto distinto al placeholder real del Punto de Venta; se corrigió la prueba para verificar el contenido existente sin modificar el POS. No hubo fallos funcionales pendientes.

### Resultado

El Issue #13 quedó implementado y probado: el futuro Punto de Venta dispone de un servicio único y atómico para confirmar ventas, y ambos roles internos pueden consultar historial y detalle sin acceder a datos de otro comercio ni a costos sensibles.

### Pendiente

Pull Request #24 mergeado a `develop` mediante el merge commit `3dfc6f7`. El Issue #13 fue cerrado como completado y no queda trabajo pendiente para este Issue.

## 2026-10-08 — Issue #11: Implementar Punto de Venta

### Rama

`feature/punto-venta`

### Objetivo

Implementar una interfaz operativa para preparar un carrito y confirmar ventas mediante el servicio transaccional existente, sin duplicar la lógica crítica de Venta, Inventario o Caja.

### Cambios realizados

- Se reemplazó el placeholder de `/punto-venta` por una pantalla POS responsive.
- ADMIN y VENDEDOR pueden buscar productos activos de su comercio por nombre o código de barras.
- Se implementó un carrito temporal en sesión con alta, incremento, cambio de cantidad, eliminación y cancelación completa.
- La pantalla relee Producto e Inventario y calcula subtotales y total en backend en cada solicitud.
- Se muestra la Caja abierta actual y una advertencia con acceso a Caja cuando no existe una disponible.
- Se incorporaron los cuatro medios de pago, observaciones y una previsualización no autoritativa del vuelto.
- La confirmación construye únicamente IDs y cantidades y delega toda la operación a `services.venta_service.confirmar_venta()`.
- Los errores `VentaError` se muestran con `flash` y conservan íntegro el carrito.
- Una confirmación exitosa vacía el carrito y redirige al detalle histórico de la Venta creada.
- Se agregó JavaScript progresivo para pago en efectivo, vuelto estimado, confirmación de cancelación y prevención visual de doble submit.
- No se modificaron `services/venta_service.py`, `database/schema.sql` ni las tablas de Inventario.

### Archivos creados o modificados

- `routes/ventas.py`
- `templates/ventas/punto_venta.html`
- `static/js/app.js`
- `tests/test_pos.py`
- `tests/test_sales.py`
- `docs/DEVLOG.md`

### Funciones o componentes importantes

- `punto_venta()`: carga Caja, carrito, productos actuales, incidencias y total para renderizar el POS.
- `add_to_cart()`: valida producto, comercio, actividad, cantidad y stock antes de agregar o acumular unidades temporales.
- `update_cart_quantity()`: actualiza una línea existente sin modificar Inventario.
- `remove_from_cart()`: elimina de forma segura una línea temporal.
- `cancel_cart()`: elimina `session["pos_cart"]` sin crear ni modificar datos persistidos.
- `confirm_pos_sale()`: obtiene la Caja abierta actual, construye items mínimos, llama a `confirmar_venta()` y administra únicamente el resultado de interfaz.
- `_search_pos_products()`: busca productos activos con Inventario y prioriza una coincidencia exacta de código de barras.
- `_get_available_pos_product()`: aplica defensa en profundidad al validar producto y comercio en operaciones del carrito.
- `_load_pos_cart()`: relee precio, stock y estado actuales, calcula importes con `Decimal` y detecta líneas problemáticas.
- `_get_pos_cart()`: obtiene una copia simple del estado temporal guardado en sesión.

### Decisiones técnicas

- El carrito es temporal porque representa una intención previa a confirmar, no una Venta persistida.
- `session["user_id"]` conserva la identidad y `session["pos_cart"]` contiene exclusivamente claves de `id_producto` y cantidades enteras. Rol y comercio continúan releyéndose desde DB mediante `g.user`.
- No se guardan precio, stock, subtotal, total, Caja, comercio, pago ni vuelto en sesión porque todos pueden cambiar o deben validarse desde datos persistidos.
- Cada modificación reasigna `session["pos_cart"]` para que Flask detecte el cambio de la cookie de sesión.
- Agregar un producto no reserva existencias. Si cambia el stock, la pantalla lo advierte y `confirmar_venta()` vuelve a validarlo bajo su transacción.
- El total visible es una previsualización calculada en backend con precios actuales; el total definitivo se recalcula nuevamente dentro de `confirmar_venta()` para evitar confiar en sesión, JavaScript o formularios manipulados.
- El POS obtiene la Caja abierta mediante `get_open_cash_register()` en cada consulta y confirmación. `id_caja` no se guarda en el carrito porque la Caja puede cerrarse mientras se prepara.
- Todos los productos se filtran y validan con `g.user["id_comercio"]`; el servicio repite la validación al confirmar como defensa en profundidad.
- `routes/ventas.py` no inserta Venta o detalles, no actualiza Inventario y no crea movimientos. La transacción continúa perteneciendo exclusivamente a `confirmar_venta()`.
- Ante `VentaError`, el servicio ya efectuó rollback y la ruta conserva el carrito para que el operador pueda corregirlo.
- Después del éxito se elimina el carrito, se informa ID, total y vuelto confirmado, y se muestra el detalle histórico.
- Quitar elimina una línea temporal; cancelar vacía todo el carrito antes de confirmar; ninguno equivale a anular una Venta ya confirmada.
- La cancelación previa requerida por Issue #11 implementa el comportamiento funcional superpuesto con Issue #18/PB32. El Issue #18 permanece abierto para revisión administrativa y trazabilidad posterior.
- No existe estado `ANULADA`, devolución, reintegro ni reversión de stock en este alcance.
- JavaScript mejora la experiencia, pero Caja, stock, precios, importes y pagos se validan siempre en backend.

### Pruebas realizadas

Se ejecutó la suite completa con:

```text
.venv\Scripts\python.exe -m pytest -q
```

Resultado: `217 passed`.

Las 36 pruebas nuevas cubren acceso anónimo, ADMIN y VENDEDOR, búsqueda por nombre y código, aislamiento, productos activos, precio de venta y stock visible, carrito mínimo en sesión, altas repetidas, cambio de cantidad, eliminación, validaciones, productos ajenos o inactivos, ausencia de reserva de stock, logout, subtotales y total desde DB, cambios de precio, Caja abierta o ausente, carrito vacío, errores del servicio, stock cambiante, pagos y cancelación repetible sin efectos persistidos.

Una prueba de integración completa autentica a VENDEDOR, agrega y modifica un producto, confirma en efectivo y verifica Venta, DetalleVenta, Inventario, MovimientoInventario, Caja, usuario, vuelto, redirect al detalle y limpieza del carrito. También se actualizó la prueba histórica que exigía mantener el POS como placeholder. Los 181 tests anteriores continúan pasando con ese comportamiento sustituido por el Issue #11.

Se ejecutó además `.venv\Scripts\python.exe -m compileall -q app.py database routes services tests utils`, sin errores.

### Problemas encontrados

La rama local `develop` estaba detrás del merge del Issue #13. Se actualizó mediante `git fetch origin` y `git pull --ff-only origin develop` hasta `3dfc6f7` antes de crear `feature/punto-venta`. La prueba histórica del Issue #13 todavía exigía que `/punto-venta` fuera un placeholder; se actualizó para reflejar el reemplazo intencional de ese comportamiento. No quedaron fallos funcionales pendientes.

### Resultado

El Issue #11 quedó implementado y probado: ambos roles internos pueden preparar, corregir, cancelar y confirmar un carrito usando siempre datos actuales y delegando la Venta atómica al servicio existente.

### Pendiente

Pull Request #25 mergeado a `develop` mediante el merge commit `22cd577`. El Issue #11 fue cerrado como completado y no queda trabajo pendiente para este Issue. La cancelación previa integrada en este mismo flujo también permitió resolver funcionalmente el Issue #18.

## 2026-10-08 — Issue #18: Cancelar venta antes de confirmar

### Implementación real

La funcionalidad de este Issue quedó implementada dentro de `feature/punto-venta` y fue integrada mediante el Pull Request #25, por lo que no se creó una rama `feature/cancelar-venta` separada.

La acción `POST /punto-venta/cancelar` elimina únicamente `session["pos_cart"]`. No crea `Venta`, `DetalleVenta` ni `MovimientoInventario`, y no modifica `Inventario` ni `Caja`. La interfaz solicita confirmación visual antes de vaciar un carrito con productos.

### Trazabilidad

La trazabilidad operativa queda registrada como:

`RF12 · PB32`

La referencia anterior a `HU12` se retiró del Issue #18 porque existe una inconsistencia en la documentación histórica: en Etapa 8 v1.1, HU12 corresponde a apertura y cierre de Caja, mientras que RF12 y PB32 describen cancelar una venta antes de confirmarla. Las versiones históricas no se reescriben retroactivamente; la corrección queda documentada en GitHub y en este registro de desarrollo.

### Pruebas y evidencia

La prueba `test_cancel_cart_is_repeatable_and_never_changes_database()` verifica que:

- un carrito con productos puede cancelarse;
- el carrito queda vacío;
- repetir la cancelación no produce inconsistencias;
- no se crea ninguna Venta ni DetalleVenta;
- no se crea MovimientoInventario;
- el stock permanece igual;
- la Caja permanece sin cambios.

No se agregaron pruebas nuevas para cerrar administrativamente este Issue. La evidencia corresponde a la suite del Issue #11, que finalizó con `217 passed`.

### Resultado

El comportamiento solicitado por RF12/PB32 quedó implementado, probado e integrado mediante el Punto de Venta. El Issue #18 fue cerrado como completado sin introducir una rama o implementación duplicada.

### Pendiente

No queda trabajo funcional pendiente para el Issue #18.

## 2026-10-08 — Issue #14: Implementar Dashboard y Estadísticas

### Rama

`feature/estadisticas`

### Objetivo

Implementar un Dashboard operativo por rol y una vista analítica exclusiva de ADMIN, calculando todas las métricas desde Ventas, DetalleVenta, Producto, Inventario y Caja existentes.

### Cambios realizados

- Se reemplazó el placeholder de Dashboard por un resumen responsive diferenciado para ADMIN y VENDEDOR.
- ADMIN visualiza ventas, cantidad y ticket promedio del día, estado de Caja, stock bajo y accesos administrativos.
- VENDEDOR visualiza la Caja actual, sus ventas acumuladas, stock bajo y accesos operativos sin información de costos o rentabilidad.
- Se reemplazó el placeholder de Estadísticas por una vista ADMIN con KPIs, rankings, stock bajo actual y gráficos.
- Se implementaron filtros para hoy, 7 días, 30 días, mes actual, todo el historial y período personalizado.
- Se agregaron agregaciones reutilizables para resumen comercial, ventas diarias, productos más vendidos, ganancia estimada, productos más rentables y stock bajo.
- Se incorporaron gráficos Chart.js de ventas por día y productos más vendidos, alimentados con JSON seguro calculado en backend.
- Los conjuntos sin ventas muestran importes en cero, rankings vacíos y estados de gráfico sin datos.
- Todas las consultas están aisladas por comercio y consideran explícitamente solo ventas `COMPLETADA`.
- No se crearon tablas, no se persistieron KPIs y no se modificaron datos operativos.

### Archivos creados o modificados

- `services/estadisticas_service.py`
- `routes/dashboard.py`
- `routes/estadisticas.py`
- `templates/dashboard/index.html`
- `templates/estadisticas/index.html`
- `templates/base.html`
- `static/js/estadisticas.js`
- `tests/test_statistics.py`
- `docs/DEVLOG.md`

### Funciones o componentes importantes

- `resolve_period()`: valida el período y produce límites inclusivos para fechas de Venta.
- `get_sales_summary()`: calcula total vendido, cantidad de ventas, ticket promedio y unidades vendidas.
- `get_daily_sales()`: agrupa ventas completadas por fecha para tabla y gráfico.
- `get_top_selling_products()`: obtiene el Top 5 por unidades usando DetalleVenta histórico.
- `get_estimated_profit()`: calcula la ganancia bruta estimada con subtotales históricos y costo actual.
- `get_top_profitable_products()`: genera el Top 5 por ganancia estimada.
- `get_low_stock_products()`: consulta el estado actual de productos activos cuyo stock no supera el mínimo.
- `get_cash_register_sales_summary()`: resume las ventas completadas de la Caja actual para VENDEDOR.
- `dashboard.index()`: selecciona únicamente los datos necesarios según el rol autenticado.
- `estadisticas.index()`: valida filtros, solicita agregaciones y prepara datos seguros para los gráficos.

### Decisiones técnicas

- Dashboard y Estadísticas son vistas derivadas; no tienen tablas propias porque cada dato se registra una sola vez y luego se reutiliza.
- Dashboard es un resumen operativo breve. Estadísticas es la vista analítica detallada de ADMIN y no se duplica dentro del Dashboard.
- ADMIN recibe métricas globales de su comercio; VENDEDOR recibe solo información operativa de la Caja actual y stock, sin ejecutar consultas de ganancia.
- VENDEDOR no ve costos, margen, ganancia o rentabilidad porque son datos económicos exclusivos del rol administrador.
- Las ventas se aíslan mediante `Venta JOIN Caja` y `Caja.id_comercio`; Inventario se aísla mediante `Producto.id_comercio`.
- El total vendido usa `SUM(Venta.total)` porque representa el importe histórico confirmado, incluso si en el futuro existen descuentos.
- Los rankings usan cantidad y subtotal de DetalleVenta, por lo que cambiar `Producto.precio_venta` no reescribe los ingresos históricos.
- Ticket promedio es total vendido dividido por cantidad de ventas; cuando no hay ventas devuelve `0.00`.
- Stock bajo actual significa `stock_actual <= stock_minimo` para productos activos e incluye agotados. No depende del filtro histórico de ventas.
- Los períodos usan `DATE(venta.fecha_hora)` con límites inclusivos coherentes. El valor por defecto y el fallback ante filtros inválidos son los últimos 30 días incluyendo hoy.
- Los importes agregados se convierten a `Decimal` y se normalizan a dos decimales en backend.
- Las ventas históricas de productos hoy inactivos permanecen en métricas y rankings; solo el stock bajo actual excluye productos inactivos.
- La métrica se llama “Ganancia bruta estimada” porque DetalleVenta no conserva costo histórico. Usa el subtotal histórico menos `Producto.precio_compra` actual por unidad.
- Si cambia el precio de compra actual, cambia la estimación histórica. Es una limitación consciente del modelo MVP y no una ganancia contable exacta.
- Chart.js solo representa arrays ya calculados por Flask; no calcula métricas ni aplica reglas de negocio.
- Dashboard y Estadísticas ejecutan únicamente `SELECT`; no realizan commits ni modifican Venta, DetalleVenta, Producto, Inventario, Caja o movimientos.
- La trazabilidad de Estadísticas corresponde a `RF14 · HU14 · PB19-PB20`. Dashboard se documenta como vista integradora sin inventar un RF/HU nuevo.

### Pruebas realizadas

Se ejecutó la suite completa con:

```text
.venv\Scripts\python.exe -m pytest -q
```

Resultado: `248 passed`.

Las 31 pruebas nuevas cubren autenticación, permisos ADMIN/VENDEDOR, Dashboard de ambos roles, métricas diarias, Caja, stock bajo, ausencia de información sensible, KPIs, rankings, precio histórico, producto inactivo histórico, costo actual, ganancia estimada, series diarias, datos para gráficos, períodos estándar, mes, todo, personalizado inclusivo, filtros inválidos, aislamiento entre dos comercios, comercio sin ventas y garantía de solo lectura.

Se ejecutó además `.venv\Scripts\python.exe -m compileall -q app.py database routes services tests utils`, sin errores.

### Problemas encontrados

La rama local `develop` estaba detrás de la integración y cierre documental de los Issues #11 y #18. Se actualizó mediante `git fetch origin` y `git pull --ff-only origin develop` hasta el commit exacto `428c76937bebebb7216faa87ac0008609b2823e3` antes de crear `feature/estadisticas`. La implementación y las pruebas no presentaron fallos funcionales pendientes.

### Resultado

El Issue #14 quedó implementado y probado: Dashboard reutiliza información operativa según el rol y Estadísticas ofrece análisis aislado por comercio sin persistir métricas ni alterar los módulos existentes.

### Pendiente

Pull Request #27 mergeado a `develop` mediante el merge commit `df1a9e3`. El Issue #14 fue cerrado como completado y no queda trabajo pendiente para este Issue.

## 2026-10-08 — Issue #15: Implementar Catálogo público

### Rama

`feature/catalogo-publico`

### Objetivo

Implementar el catálogo informativo y público de StockFlow para que cualquier visitante pueda seleccionar un comercio activo y consultar sus productos publicados, sin iniciar sesión y sin incorporar compra, reserva, carrito o búsqueda global entre comercios.

### Cambios realizados

- Se reemplazó el placeholder de Catálogo por una entrada pública que lista únicamente comercios activos.
- Se agregó el catálogo específico `GET /catalogo/<commerce_id>` como fuente explícita de los productos de una tienda.
- Se incorporaron búsqueda parcial por nombre y filtro por categorías activas que tienen publicaciones vigentes.
- Se muestran nombre, categoría, descripción e imagen opcional mediante una proyección pública acotada.
- Se incorporaron los estados derivados `Disponible`, `Pocas unidades` y `Agotado` sin exponer cantidades.
- Se aplicaron de forma conjunta los filtros de comercio, producto activo, visibilidad pública, categoría activa e Inventario existente.
- Se implementó la publicación condicional de `precio_venta`: se muestra el precio actual cuando está habilitado y `Precio no publicado` cuando está oculto.
- Se centralizó la regla de disponibilidad en el servicio de Inventario para que Inventario y Catálogo compartan exactamente el mismo cálculo.
- Se eliminó el stub histórico `NotImplemented` de Inventario, reemplazado por el helper compartido, sin alterar movimientos de stock.
- Se agregaron estados claros para comercio sin publicaciones, búsqueda sin coincidencias y categoría inválida o ajena.
- Se cubrió funcionalmente el alcance del Issue #17 sin crear columnas ni una segunda implementación del precio.

### Archivos creados o modificados

- `services/catalogo_service.py`
- `services/inventario_service.py`
- `routes/catalogo.py`
- `routes/inventario.py`
- `templates/catalogo/comercios.html`
- `templates/catalogo/index.html`
- `tests/test_catalog.py`
- `docs/DEVLOG.md`

### Funciones o componentes importantes

- `get_public_commerces()`: devuelve los datos básicos permitidos de los comercios activos.
- `get_public_commerce()`: valida que la tienda solicitada exista y esté activa.
- `get_public_categories()`: obtiene categorías activas con productos públicos e Inventario dentro del comercio seleccionado.
- `get_public_catalog()`: aplica los filtros públicos y devuelve solo nombre, descripción, imagen, categoría, precio permitido y disponibilidad derivada.
- `get_availability_status()`: centraliza en Inventario la regla compartida para los tres estados de disponibilidad.
- `catalogo.index()`: presenta la selección explícita de comercios activos.
- `catalogo.commerce_catalog()`: resuelve tienda, búsqueda, categoría y proyección pública sin modificar la base.

### Decisiones técnicas

- Catálogo no tiene tabla propia porque Producto, Inventario, Categoría y Comercio ya son las fuentes vigentes. Duplicar esos datos introduciría sincronización innecesaria e inconsistencias.
- Producto conserva nombre, descripción, imagen, estado, banderas y `precio_venta`; Inventario conserva `stock_actual` y `stock_minimo`. Catálogo únicamente consulta y proyecta.
- El comercio se identifica explícitamente con `commerce_id` en la URL. `/catalogo` solo permite elegir una tienda activa y no implementa HU18 ni búsqueda de productos entre comercios.
- Un producto se publica únicamente si pertenece al comercio solicitado, está activo, tiene `visible_catalogo = 1`, pertenece a una categoría activa y posee Inventario. El `INNER JOIN` evita publicar productos con información operativa incompleta.
- Las categorías desactivadas ocultan de forma derivada sus productos sin cambiar ni eliminar el Producto. Las opciones del filtro se limitan a categorías activas con publicaciones vigentes.
- Una categoría inválida o de otro comercio se ignora de manera segura y se informa al visitante; nunca se usa para revelar información ajena.
- La disponibilidad no se persiste. Cada request aplica la regla compartida sobre el Inventario actual: cero es `Agotado`, un valor positivo menor o igual al mínimo es `Pocas unidades` y un valor mayor al mínimo es `Disponible`.
- El template nunca recibe cantidades exactas. El servicio usa stock y mínimo solo para derivar el estado y construye un diccionario público sin IDs de Producto, Inventario, usuario, Caja o Venta.
- `mostrar_precio_catalogo` controla únicamente la proyección. Si está deshabilitado, el servicio entrega `price = None`; por eso el precio oculto no queda presente en HTML, atributos o JSON.
- No existe un segundo precio: el único importe público posible es el `Producto.precio_venta` actual. Las cuatro combinaciones de `visible_catalogo` y `mostrar_precio_catalogo` respetan la precedencia de la visibilidad.
- Catálogo representa información vigente, por lo que un cambio en `precio_venta` se refleja en la siguiente consulta. En cambio, `DetalleVenta` conserva el precio histórico de una operación confirmada.
- Todas las consultas se aíslan por comercio. Los productos, categorías, precios, costos y existencias de otra tienda no integran la proyección solicitada.
- Además de filtrar por `commerce_id`, los joins entre Producto y Categoría exigen que ambos pertenezcan al mismo comercio. Esta defensa en profundidad evita proyectar asociaciones inconsistentes introducidas directamente en SQLite o por futuras regresiones fuera del CRUD validado.
- El acceso es anónimo y de solo lectura. Los endpoints públicos no ejecutan `INSERT`, `UPDATE`, `DELETE` ni `commit`.
- Un comercio activo sin publicaciones muestra un estado vacío específico; una búsqueda o filtro sin coincidencias muestra un estado de resultados distinto.
- La superposición con el Issue #17 se resolvió reutilizando las banderas ya administradas por Productos y la única fuente de precio existente. Después de la revisión y del merge del PR #29, el Issue #17 fue cerrado como completado sin crear una implementación duplicada.

Trazabilidad del Catálogo:

`RF15-RF17 · HU15-HU17 · PB21-PB24 · PB31`

Trazabilidad específica de publicación de precio del Issue #17:

`RF05 · RF17 · HU05 · HU17 · PB31`

### Pruebas realizadas

Se ejecutó la suite completa con:

```text
.venv\Scripts\python.exe -m pytest -q
```

Resultado: `275 passed`.

Las 27 pruebas nuevas cubren acceso público sin sesión, selector de comercios activos, comercios inexistentes o inactivos, proyección permitida, valores centinela de costo y stock, las cuatro combinaciones de publicación del Issue #17, precio oculto, producto oculto, producto y categoría inactivos, desactivación de categoría, ausencia de Inventario, los tres estados derivados, cambios sucesivos de stock, precio actual, búsqueda parcial, filtro válido, categoría inválida o ajena, aislamiento entre dos comercios, rechazo de asociaciones Producto-Categoría inconsistentes entre comercios, comercio vacío, claves exactas de la proyección, integración con una Venta confirmada y garantía de solo lectura.

Los 248 tests anteriores continúan pasando. Se ejecutó además `.venv\Scripts\python.exe -m compileall -q app.py database routes services tests utils`, sin errores.

### Problemas encontrados

La rama local `develop` estaba detrás del merge y cierre documental del Issue #14. Se sincronizó mediante `git fetch origin` y `git pull --ff-only origin develop` hasta el commit exacto `35850a2223f093ad4b3620f1471026eebc9921b6` antes de crear `feature/catalogo-publico`.

En el primer pase de la suite nueva, una búsqueda de prueba usaba el término `oculto`, que también coincidía correctamente con un producto público llamado `Producto precio oculto`. Se cambió el dato de prueba por un término exclusivo del producto oculto; no existía un fallo funcional en la consulta.

### Resultado

El Issue #15 quedó implementado y probado: el visitante puede seleccionar una tienda activa, buscar y filtrar publicaciones vigentes, consultar disponibilidad sin conocer cantidades y ver el precio actual únicamente cuando el comercio decidió publicarlo. Inventario, Productos y Punto de Venta siguen siendo las fuentes únicas de los datos y cualquier cambio se refleja en la siguiente consulta pública.

El Issue #17 quedó cubierto funcionalmente por la misma implementación y por pruebas explícitas de sus cuatro combinaciones, sin agregar esquema ni precio alternativo.

### Cierre de integración

El Pull Request #29 fue mergeado a `develop` mediante el merge commit `85377fc`.

El Issue #15 fue cerrado como completado después de verificar sus criterios de aceptación. El Issue #17 también fue cerrado como completado porque su alcance quedó cubierto por la misma implementación: las banderas ya existían en Productos y el Catálogo incorporó la proyección condicional del único `precio_venta`.

No se creó una rama `feature/precio-publico` separada porque hubiera duplicado trabajo ya integrado y probado.

### Pendiente

No queda trabajo funcional pendiente para los Issues #15 y #17. El siguiente bloque corresponde al Issue #16 de testing e integración final del MVP.

## 2026-10-08 — Issue #16: Testing e integración del MVP

### Rama

`test/integracion-mvp`

### Objetivo

Validar como conjunto el MVP ya implementado, agregar evidencia cross-module de sus flujos críticos, preparar datos demo reproducibles y actualizar la documentación técnica antes de promover una versión revisada. Este Issue no crea un módulo ni agrega reglas de negocio nuevas.

### Estado base

- `develop`: `87bd4cc7f601d64507efde2ef673fc469e635177`.
- Suite recibida: `275 passed`.
- Trazabilidad principal: `PB28 · PB29 · PB30`.

### Cambios realizados

- Se agregaron seis pruebas de integración del MVP que recorren rutas HTTP, persistencia y consumidores posteriores.
- Se implementaron escenarios negativos cross-module para ausencia de Caja y cambio de stock antes de confirmar.
- Se agregó una matriz representativa de permisos para visitante, VENDEDOR y ADMIN.
- Se verificó el inicio real desde un archivo SQLite inexistente, las nueve tablas, claves foráneas y `/health`.
- Se incorporó un seed manual para demo con base separada, credenciales conocidas, productos públicos/ocultos y distintos estados de Inventario.
- Se agregaron dos pruebas del seed: contenido y credenciales; protección contra sobrescritura y `--reset` explícito.
- Se actualizó README para describir en presente el MVP real, instalación, configuración, ejecución, demo, tests y estrategia de ramas.
- Se creó `docs/TESTING_MVP.md` con alcance automatizado, rollback, aislamiento, checklist visual e incidencias.
- Se auditó deuda y rutas. El template placeholder no tenía referencias activas y fue eliminado.
- Durante la review se corrigió la clasificación diaria de Ventas para convertir el timestamp UTC persistido a fecha local antes de filtrar o agrupar Estadísticas.

### Archivos creados o modificados

- `tests/test_mvp_integration.py`
- `tests/test_seed_demo.py`
- `scripts/__init__.py`
- `scripts/seed_demo.py`
- `README.md`
- `docs/TESTING_MVP.md`
- `docs/DEVLOG.md`
- `services/estadisticas_service.py`
- `templates/placeholder.html` (eliminado por no tener referencias)

### Pruebas de integración

Las pruebas nuevas no repiten cada test unitario existente. Conectan Catálogo, autenticación, permisos, Caja, POS, Venta, DetalleVenta, Inventario, MovimientoInventario, Historial, Dashboard y Estadísticas mediante una base temporal real.

La matriz de acceso verifica que el visitante solo accede a rutas públicas, VENDEDOR utiliza los módulos operativos permitidos y ADMIN accede también a Productos, Categorías, movimientos y Estadísticas.

Una operación completa de Comercio A se compara contra un snapshot de Comercio B para confirmar que B conserva stock, Caja y Ventas, mantiene métricas en cero y no recibe datos de A en su Catálogo.

### Flujo end-to-end

El escenario principal comienza con un producto público y stock superior al mínimo. Un visitante ve `Disponible`, el precio publicado y otro producto con `Precio no publicado`. VENDEDOR inicia sesión, abre Caja, agrega el producto al POS y confirma una Venta en efectivo.

La prueba verifica cabecera de Venta, DetalleVenta, usuario, Caja, medio de pago, dinero recibido, vuelto, descuento de Inventario y Movimiento `VENTA`. Luego comprueba Historial, resumen de Caja, Dashboard de VENDEDOR, Dashboard ADMIN, Estadísticas, ranking, unidades y ganancia estimada.

Después de la Venta, una nueva consulta de Catálogo deriva `Pocas unidades` desde el Inventario actual. Finalmente ADMIN cierra la Caja con efectivo contado igual al esperado y diferencia cero.

### Casos negativos

- Sin Caja abierta: la confirmación se rechaza, el carrito permanece y no se crean Venta, DetalleVenta o Movimiento ni se modifica stock.
- Stock reducido después de agregar al carrito: la confirmación relee las existencias, evita la sobreventa, conserva el carrito y no deja escrituras parciales.
- El rollback profundo ya estaba cubierto por `test_deep_database_failure_rolls_back_every_sale_change`, que fuerza un fallo intermedio con un trigger y verifica reversión de Venta, detalles, Inventario y movimientos. No se duplicó esa prueba correctamente focalizada.

### Base limpia

Una prueba parte de una ruta cuyo archivo no existe. `create_app()` crea la carpeta y la base, ejecuta `schema.sql`, genera exactamente las nueve tablas funcionales, mantiene `PRAGMA foreign_keys = ON` en la conexión y permite consultar `/health`.

No fue necesario modificar el esquema ni agregar migraciones.

### Datos demo

`scripts/seed_demo.py` crea por defecto `database/stockflow_demo.db`, archivo ya cubierto por `.gitignore`. La herramienta es manual, no se ejecuta desde la aplicación y no toca `database/stockflow.db`.

El seed genera un Comercio, ADMIN, VENDEDOR, dos Categorías, cuatro Productos e Inventarios con disponibilidad variada, precio publicado, precio oculto y producto oculto. La demo comienza sin Caja abierta para demostrar el flujo real.

Las credenciales `admin@stockflow.demo` y `vendedor@stockflow.demo`, con contraseña `StockFlow123!`, están identificadas exclusivamente como demo/desarrollo local y se almacenan con hash. Una base existente no se sobrescribe salvo que el operador use `--reset` de forma explícita; también puede indicarse otra ruta con `--database`.

### README

README ahora diferencia alcance implementado y exclusiones, documenta roles, arquitectura, transacción de Venta, relación entre POS e Inventario, Catálogo derivado, estructura real, instalación para PowerShell/Linux/macOS, variables `STOCKFLOW_SECRET_KEY` y `STOCKFLOW_DATABASE`, creación automática del esquema, seed demo, credenciales, ejecución, URLs, `/health`, tests y ramas.

El documento presenta StockFlow como MVP/demo académico funcional y no como software listo para producción.

### Incidencias reales

Se detectó que `Venta.fecha_hora` se persiste mediante `CURRENT_TIMESTAMP` de SQLite en UTC, mientras los períodos diarios se resolvían con la fecha local de Python y las consultas usaban `DATE(v.fecha_hora)` sin conversión. En zonas distintas de UTC, una Venta cercana a medianoche podía existir correctamente en Historial y Caja, pero quedar clasificada en otro día para Dashboard y Estadísticas.

La resolución aplica `DATE(v.fecha_hora, 'localtime')` de forma consistente al filtrar, seleccionar, agrupar y ordenar por fecha. No se modificaron timestamps persistidos, esquema ni datos históricos. Una prueba portable construye una hora local controlada, la convierte a UTC y comprueba que resumen y serie diaria la asignen al día local.

Durante la construcción de pruebas se corrigieron dos supuestos del propio test: VENDEDOR no accede al historial administrativo de movimientos y las conexiones SQLite deben cerrarse explícitamente antes de reemplazar un archivo en Windows. No se modificó código funcional por estos ajustes.

### Decisiones técnicas

- #16 agrega evidencia de integración, no un módulo nuevo, porque todas las capacidades de negocio del MVP ya estaban implementadas.
- Una prueba unitaria aísla una regla; una prueba de integración conecta componentes reales; el escenario end-to-end atraviesa HTTP, sesión, base y módulos consumidores.
- La atomicidad se demuestra con la prueba existente de fallo profundo y con nuevos negativos que verifican ausencia de persistencia parcial.
- El aislamiento se verifica con dos comercios y snapshots de stock, Caja y Ventas, además de consultas separadas de Dashboard, Estadísticas y Catálogo.
- El efecto Venta → Catálogo se comprueba recargando la ruta pública después del descuento real de Inventario; no se almacena disponibilidad.
- Los timestamps de Venta permanecen almacenados en UTC. Solo las consultas por día calendario aplican `localtime`, alineándose con `date.today()` usado por Dashboard y la resolución de períodos.
- El seed es manual porque una base normal no debe recibir usuarios, contraseñas conocidas o datos ficticios automáticamente.
- La creación atómica en un archivo temporal evita dejar una base demo parcial. El reemplazo solo está habilitado mediante `--reset` explícito.
- No se realizó ni se declara una validación visual humana. `TESTING_MVP.md` conserva una checklist desktop/mobile pendiente antes de promover `develop` a `main`.
- Se eliminaron únicamente el template placeholder sin referencias; las menciones históricas del DEVLOG y los atributos HTML `placeholder` se conservaron.
- La rama prepara evidencia para review y PR hacia `develop`; no autoriza ni realiza una promoción directa a `main`.

### Pruebas realizadas

Se ejecutó la suite completa con:

```text
.venv\Scripts\python.exe -m pytest -q
```

Resultado: `283 passed`.

Se agregaron ocho pruebas: seis escenarios en `test_mvp_integration.py` y dos del seed en `test_seed_demo.py`. Las 275 pruebas recibidas continúan pasando.

También se ejecutó:

```text
.venv\Scripts\python.exe -m compileall -q app.py database routes services scripts tests utils
git diff --check
git grep -n -E "TODO|FIXME|NotImplemented|placeholder"
```

La auditoría no encontró stubs activos. Las coincidencias restantes son texto histórico, atributos de formularios o variables auxiliares de pruebas.

### Resultado

El MVP quedó integrado y respaldado por evidencia automatizada de flujo completo, permisos, errores seguros, rollback, aislamiento, base limpia y datos demo reproducibles. La incidencia de clasificación temporal quedó corregida en consultas y cubierta por regresión, sin modificar el esquema ni los datos persistidos.

### Pendiente

Quedan pendientes la review de `test/integracion-mvp`, el Pull Request hacia `develop` y la validación visual humana registrada en `docs/TESTING_MVP.md`. Después de esas instancias corresponderá revisar un PR separado `develop → main`.

El Issue #16 permanece abierto. La rama continúa en review; no se hizo merge ni Pull Request.
