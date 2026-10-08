# Registro de testing e integración del MVP

## Corte

- Fecha: 2026-10-08
- Rama de corrección actual: `fix/ui-etapa12`
- Base: `develop` en `665c8e147305cc0dcd1b41563a4bafdaf0a3c743`
- Suite automatizada: `296 passed`
- Pruebas agregadas: 8 de integración, 6 estructurales de navegación y 7 de polish/presentación temporal
- Trazabilidad principal: `PB28 · PB29 · PB30`

## Automatizado

La suite se ejecutó con:

```text
.venv\Scripts\python.exe -m pytest -q
```

También se verificó:

```text
.venv\Scripts\python.exe -m compileall -q app.py database routes services scripts tests utils
git diff --check
```

### Módulos cubiertos

- creación del esquema SQLite y claves foráneas;
- autenticación, sesiones y permisos ADMIN/VENDEDOR;
- Productos y Categorías;
- Inventario y MovimientoInventario;
- Caja;
- Venta y DetalleVenta;
- Punto de Venta;
- Dashboard y Estadísticas;
- Catálogo público y precio condicional;
- aislamiento entre comercios;
- seed demo manual y seguro.
- shell interno responsive, navegación por rol y separación del layout público.

### Navegación y shell visual

`tests/test_ui_navigation.py` agrega seis casos estructurales para la corrección INC-02. Verifican que ADMIN reciba Dashboard, Punto de venta, Caja, Inventario, Productos, Ventas y Estadísticas; que la navegación persista en Caja y Productos; que VENDEDOR vea únicamente sus cinco secciones operativas; y que Catálogo y Login no expongan el sidebar interno. También comprueban que la sección actual se identifique con `aria-current="page"` y que exista el disparador del offcanvas móvil.

Estas pruebas validan la estructura renderizada y los permisos ya existentes. No sustituyen la revisión humana de contraste, composición, scroll, densidad o ergonomía en viewports reales.

### Segunda revisión visual desktop

`tests/test_datetime_display.py` agrega siete casos para el polish posterior: conversión portable de timestamp SQLite UTC a la zona local del sistema, fallbacks seguros, soporte de valores `datetime`, render local en Dashboard, Caja, Ventas, detalle y Movimientos, y presencia de anchos específicos en los inputs numéricos de Inventario y POS.

La persistencia continúa en UTC. El filtro Jinja `local_datetime` resuelve únicamente la representación textual `dd/mm/aaaa hh:mm`; la clasificación diaria de Estadísticas conserva de forma independiente `DATE(v.fecha_hora, 'localtime')`.

### Flujos críticos cross-module

`tests/test_mvp_integration.py` agrega seis escenarios:

1. Flujo end-to-end mediante HTTP: Catálogo anónimo → login VENDEDOR → apertura de Caja → carrito POS → confirmación en efectivo → Venta/Detalle → Inventario/Movimiento → Historial/Caja/Dashboard → Estadísticas ADMIN → Catálogo actualizado → cierre de Caja.
2. Confirmación sin Caja abierta: no persiste Venta, Detalle ni Movimiento; conserva stock y carrito.
3. Stock reducido después de agregar al carrito: la confirmación relee existencias, rechaza la operación completa y conserva el carrito para corregirlo.
4. Matriz representativa de accesos para visitante, VENDEDOR y ADMIN.
5. Inicio desde una ruta de base inexistente: `create_app()` crea las nueve tablas, activa claves foráneas y responde correctamente en `/health`.
6. Clasificación temporal portable: una Venta con timestamp UTC cercano al cambio de día se filtra y agrupa según la fecha calendario local de la máquina.

El flujo principal parte con stock mayor al mínimo y Catálogo `Disponible`; una Venta reduce el stock hasta el mínimo y la siguiente consulta pública muestra `Pocas unidades`. El precio público continúa dependiendo de `mostrar_precio_catalogo` y nunca usa un importe alternativo.

### Caja y reportes

La integración comprueba que una Venta en efectivo:

- incrementa cantidad y total vendido de la Caja;
- suma el total de la Venta al efectivo esperado, no `dinero_recibido`;
- aparece en Historial y detalle;
- alimenta Dashboard y Estadísticas;
- actualiza unidades, ranking y ganancia estimada según costo actual;
- permite un cierre exacto con estado `CERRADA`, efectivo contado y diferencia derivada.

### Atomicidad y rollback

La prueba existente `tests/test_sales.py::test_deep_database_failure_rolls_back_every_sale_change` fuerza mediante un trigger SQLite un fallo al insertar MovimientoInventario. Verifica que no persista Venta, DetalleVenta ni Movimiento y que el Inventario conserve stock y fecha anteriores.

No se duplicó ese escenario en el archivo cross-module porque ya prueba explícitamente la transacción completa `Venta → Detalle → Inventario → Movimiento`. Las pruebas negativas nuevas vuelven a comprobar que no existen escrituras parciales ante falta de Caja o stock insuficiente.

### Aislamiento

El escenario end-to-end mantiene dos comercios. Después de operar y cerrar Caja en A, verifica que B conserve exactamente su stock, Caja y cantidad de Ventas; sus métricas permanecen en cero y su Catálogo no expone productos de A.

Las rutas internas obtienen el comercio desde el usuario autenticado. El Catálogo usa el comercio explícito de la URL y exige coherencia de comercio en los joins públicos.

### Base limpia

Una prueba parte de un archivo SQLite inexistente y verifica:

- creación automática de la ruta y el archivo;
- nueve tablas funcionales exactas;
- `PRAGMA foreign_keys = ON` en la conexión de Flask;
- respuesta `200` y JSON esperado de `/health`.

No se modificó `database/schema.sql` ni se agregaron migraciones.

### Seed demo

`scripts/seed_demo.py` crea manualmente `database/stockflow_demo.db` con:

- un Comercio activo;
- ADMIN y VENDEDOR con contraseñas hasheadas;
- dos Categorías;
- cuatro Productos e Inventarios;
- estados Disponible, Pocas unidades y Agotado;
- precio público, precio oculto y producto oculto;
- ninguna Caja abierta inicialmente.

Dos pruebas verifican contenido, hashes, login real de ambas credenciales, flags públicos, ausencia de Caja, rechazo de sobrescritura y recreación únicamente con `--reset`.

El seed no se importa ni ejecuta desde `create_app()` y nunca crea usuarios automáticamente en una base normal.

## Manual / visual

La validación visual humana fue completada por Axel después del polish final. Desktop y mobile en viewport `390×844` quedaron aprobados; la evidencia automatizada complementa esta revisión y no la sustituye.

Validación visual humana completada:

- [x] Catálogo desktop
- [x] Catálogo mobile
- [x] Login desktop
- [x] Login mobile
- [x] Dashboard ADMIN
- [x] Dashboard VENDEDOR
- [x] Productos
- [x] Formularios de Producto y Categorías
- [x] Inventario
- [x] Ajuste e historial de movimientos
- [x] POS
- [x] Caja
- [x] Ventas
- [x] Detalle de Venta
- [x] Estadísticas
- [x] Mensajes de error

Validación humana completada en desktop y viewport mobile `390×844`.

### Evidencia visual aprobada

En desktop se verificaron Catálogo público, Login, Dashboard ADMIN, POS, Caja cerrada y abierta, Inventario, Productos, Ventas y Estadísticas. También se aprobaron la navegación persistente, la indicación del módulo activo, la presentación local de timestamps y la legibilidad de inputs numéricos.

En mobile `390×844` se verificaron Dashboard, menú hamburguesa y offcanvas completo, navegación ADMIN, POS, Caja, Inventario, Productos, Ventas, Estadísticas, Catálogo público y Login.

No se observó overflow horizontal global. El sidebar desktop se reemplaza por el offcanvas mobile; cards y KPIs se apilan; los formularios pasan a disposición vertical; la búsqueda, los productos y el carrito del POS se apilan; el grid desktop del Catálogo pasa a una columna; y Estadísticas apila KPIs, gráficos y rankings.

Las tablas de Inventario, Productos, Ventas y productos del POS conservan deliberadamente su estructura tabular dentro de contenedores `table-responsive` con scroll horizontal contenido. Esta decisión preserva su legibilidad en mobile y no constituye una incidencia, ya que no genera overflow en la página.

## Incidencias

| ID | Caso | Resultado | Incidencia | Resolución |
| --- | --- | --- | --- | --- |
| INC-01 | Venta cercana al cambio de día local | Corregido | `CURRENT_TIMESTAMP` persiste UTC, pero los filtros diarios comparaban `DATE(fecha_hora)` contra fechas locales de Python. Dashboard y Estadísticas podían excluir una Venta correctamente persistida. | Las consultas usan `DATE(v.fecha_hora, 'localtime')` para filtrar, seleccionar, agrupar y ordenar; una regresión portable verifica resumen y serie diaria. |
| INC-02 | Shell visual y navegación interna de Etapa 12 | Resuelto | Las vistas usaban una barra superior mínima y estilos Bootstrap claros, sin navegación persistente, jerarquía visual ni diferenciación suficiente por rol. | Se incorporaron sidebar desktop, offcanvas móvil, menú ADMIN/VENDEDOR, estado activo accesible, header público separado y tema oscuro centralizado. Se agregaron seis regresiones estructurales y la validación humana desktop/mobile quedó aprobada. |
| INC-03 | Timestamps UTC mostrados en interfaz | Resuelto | Caja, Dashboard, Ventas y Movimientos proyectaban directamente valores SQLite UTC, por lo que la hora visible podía diferir de la hora local del equipo. | Se registró el filtro Jinja `local_datetime`, que interpreta strings SQLite como UTC y usa `astimezone()` para presentar la zona local. No cambia schema, datos ni agregaciones de Estadísticas; la presentación local fue aprobada en la validación humana. |

Durante la construcción de las nuevas pruebas se corrigieron dos supuestos del propio test: el historial de movimientos es ADMIN y las conexiones SQLite deben cerrarse explícitamente antes de reemplazar un archivo en Windows. Ninguno requirió modificar reglas o código funcional del MVP.

## Auditoría de rutas y deuda

Se comprobaron rutas funcionales para `/login`, `/dashboard`, `/productos`, `/categorias`, `/inventario`, `/inventario/movimientos`, `/punto-venta`, `/ventas`, `/caja`, `/estadisticas`, `/catalogo`, `/catalogo/<commerce_id>` y `/health`.

La búsqueda de `TODO`, `FIXME`, `NotImplemented` y `placeholder` no encontró stubs activos en Python. Las coincidencias restantes corresponden a atributos HTML, nombres auxiliares de tests o referencias históricas del DEVLOG. `templates/placeholder.html` no tenía referencias y se eliminó.

## Interpretación para la defensa

- Una prueba unitaria aísla una regla o función; una prueba de integración conecta componentes reales; el flujo end-to-end recorre rutas HTTP y verifica efectos persistidos y vistas consumidoras.
- Venta es dueña de una transacción única. Si falla una etapa, SQLite revierte cabecera, detalles, stock y movimientos.
- No queda stock negativo porque la confirmación relee y valida existencias dentro de la transacción; el carrito no reserva stock.
- Caja usa el total confirmado y suma solo Ventas en efectivo al efectivo esperado.
- Inventario es la fuente actual; Catálogo deriva disponibilidad, mientras Dashboard y Estadísticas agregan Ventas confirmadas.
- Catálogo no tiene tabla porque reutiliza Producto, Categoría e Inventario sin duplicar datos.
- El aislamiento combina el comercio del usuario autenticado, filtros SQL y pruebas con dos comercios.
- El seed existe para una demostración reproducible, es manual, separado de la base normal y contiene credenciales conocidas exclusivamente locales.
- La corrección `fix/ui-etapa12` todavía necesita review e integración a `develop` antes de una promoción posterior y revisada hacia `main`; la validación visual humana ya fue completada.

## Resultado

La evidencia automatizada del MVP queda aprobada con `296 passed` y la validación visual humana desktop/mobile quedó completada. INC-01, INC-02 e INC-03 están resueltas y cubiertas por regresiones sin modificar esquema ni reglas de negocio. Restan la review y el Pull Request de la corrección hacia `develop`, su merge y el cierre del Issue #16 antes de evaluar una promoción posterior hacia `main`.
