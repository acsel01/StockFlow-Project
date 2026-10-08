# Registro de testing e integración del MVP

## Corte

- Fecha: 2026-10-08
- Rama: `test/integracion-mvp`
- Base: `develop` en `87bd4cc7f601d64507efde2ef673fc469e635177`
- Suite automatizada: `282 passed`
- Pruebas agregadas en este bloque: 7
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

### Flujos críticos cross-module

`tests/test_mvp_integration.py` agrega cinco escenarios:

1. Flujo end-to-end mediante HTTP: Catálogo anónimo → login VENDEDOR → apertura de Caja → carrito POS → confirmación en efectivo → Venta/Detalle → Inventario/Movimiento → Historial/Caja/Dashboard → Estadísticas ADMIN → Catálogo actualizado → cierre de Caja.
2. Confirmación sin Caja abierta: no persiste Venta, Detalle ni Movimiento; conserva stock y carrito.
3. Stock reducido después de agregar al carrito: la confirmación relee existencias, rechaza la operación completa y conserva el carrito para corregirlo.
4. Matriz representativa de accesos para visitante, VENDEDOR y ADMIN.
5. Inicio desde una ruta de base inexistente: `create_app()` crea las nueve tablas, activa claves foráneas y responde correctamente en `/health`.

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

No se realizó una validación visual humana completa en navegador para este corte. La evidencia automatizada valida rutas, permisos, contenido funcional y estructura Bootstrap, pero no sustituye una revisión visual desktop/mobile.

Pendiente de validación visual humana antes de promover `develop` a `main`:

- [ ] Catálogo desktop
- [ ] Catálogo mobile
- [ ] Dashboard ADMIN
- [ ] Dashboard VENDEDOR
- [ ] Productos
- [ ] Inventario
- [ ] POS
- [ ] Caja
- [ ] Ventas
- [ ] Estadísticas
- [ ] Mensajes de error

## Incidencias

| ID | Caso | Resultado | Incidencia | Resolución |
| --- | --- | --- | --- | --- |
| — | Suite e integración del MVP | Aprobado | No se detectaron incidencias funcionales nuevas durante este bloque. | No aplica. |

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
- `develop` todavía necesita review de esta rama y validación visual antes de una promoción revisada hacia `main`.

## Resultado

La evidencia automatizada del MVP queda aprobada con `282 passed`. No se detectaron bugs funcionales nuevos ni se modificaron reglas de negocio. La promoción queda condicionada a review, Pull Request hacia `develop` y validación visual humana.
