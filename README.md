# StockFlow

StockFlow es un sistema web de gestión comercial, inventario y consulta pública de disponibilidad para kioscos, almacenes y otros comercios pequeños. Integra la operación interna con un catálogo informativo que reutiliza el stock y los precios vigentes.

Es un **MVP académico funcional y una demo local**. No está presentado ni configurado como un sistema listo para producción.

## Alcance del MVP

La versión implementada incluye:

- autenticación con sesiones y permisos para ADMIN y VENDEDOR;
- Dashboard operativo diferenciado por rol;
- gestión de Productos y Categorías con baja lógica;
- Inventario, stock mínimo y trazabilidad de movimientos;
- apertura, seguimiento y cierre de Caja;
- Punto de Venta con carrito temporal y validación al confirmar;
- Ventas atómicas con DetalleVenta, descuento de Inventario y MovimientoInventario;
- historial y detalle de ventas con precios históricos;
- Estadísticas de ventas, rankings, stock bajo y ganancia bruta estimada;
- Catálogo público por comercio, búsqueda, categorías y disponibilidad derivada;
- publicación opcional del precio de venta actual;
- aislamiento de datos entre comercios;
- endpoint de salud y creación automática del esquema SQLite;
- suite automatizada con pruebas unitarias, de integración y end-to-end.

Quedan fuera del MVP:

- compra, carrito, reserva o pago en línea;
- cuentas de clientes, favoritos, delivery o recomendaciones;
- búsqueda global de productos entre comercios (HU18);
- Mercado Pago, facturación fiscal, proveedores o devoluciones;
- múltiples sucursales por comercio;
- geolocalización y despliegue productivo.

## Roles

- **ADMIN:** accede a Dashboard, Productos, Categorías, Inventario y movimientos, Punto de Venta, Caja, Ventas y Estadísticas.
- **VENDEDOR:** accede al Dashboard operativo, consulta de Inventario, Punto de Venta, Caja y Ventas. No administra Productos, Categorías, movimientos manuales ni Estadísticas económicas.
- **VISITANTE:** sin autenticación, puede seleccionar un comercio activo y consultar su Catálogo público.

No existe una cuenta de Cliente dentro del MVP.

## Arquitectura y reglas centrales

StockFlow usa una aplicación Flask monolítica modular:

```text
Navegador
   │
   ▼
Templates HTML + Bootstrap + CSS/JS
   │
   ▼
Flask / routes
   │
   ▼
services / reglas y consultas reutilizables
   │
   ▼
SQLite
```

El esquema tiene nueve tablas funcionales: Comercio, Usuario, Categoría, Producto, Inventario, MovimientoInventario, Caja, Venta y DetalleVenta.

Confirmar una Venta se ejecuta dentro de una única transacción: valida usuario, Caja, productos, precios y stock actuales; crea Venta y DetalleVenta; descuenta Inventario; registra MovimientoInventario y confirma todo junto. Ante un error se revierte la operación completa, por lo que no quedan ventas parciales ni stock negativo.

El carrito del POS no reserva existencias. La confirmación relee la base y rechaza la operación si el stock cambió mientras el carrito estaba abierto.

El Catálogo no posee una tabla propia: proyecta Producto, Categoría e Inventario. La disponibilidad se deriva en cada consulta y el único precio público posible es `Producto.precio_venta`, condicionado por `mostrar_precio_catalogo`. DetalleVenta, en cambio, conserva el precio histórico confirmado.

## Tecnologías

| Capa | Tecnología | Uso |
| --- | --- | --- |
| Backend | Python 3.10+ y Flask 3 | Rutas, sesiones y aplicación web |
| Persistencia | SQLite | Base local y transacciones |
| Frontend | HTML5, Bootstrap, CSS y JavaScript | Interfaz responsive |
| Gráficos | Chart.js | Dashboard analítico y Estadísticas |
| Seguridad | Werkzeug | Hash y verificación de contraseñas |
| Testing | pytest | Pruebas automatizadas |

No se utiliza ORM ni se requieren dependencias externas adicionales para crear datos demo.

## Estructura del repositorio

```text
StockFlow-Project/
├── app.py
├── requirements.txt
├── README.md
├── database/
│   ├── db.py
│   └── schema.sql
├── routes/
│   ├── auth.py
│   ├── dashboard.py
│   ├── productos.py
│   ├── inventario.py
│   ├── ventas.py
│   ├── caja.py
│   ├── estadisticas.py
│   └── catalogo.py
├── services/
│   ├── venta_service.py
│   ├── inventario_service.py
│   ├── estadisticas_service.py
│   └── catalogo_service.py
├── scripts/
│   └── seed_demo.py
├── templates/
├── static/
├── tests/
│   ├── test_mvp_integration.py
│   └── ...
└── docs/
    ├── DEVLOG.md
    └── TESTING_MVP.md
```

## Instalación

### Windows PowerShell

```powershell
git clone https://github.com/acsel01/StockFlow-Project.git
cd StockFlow-Project
git switch develop

py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Linux o macOS

```bash
git clone https://github.com/acsel01/StockFlow-Project.git
cd StockFlow-Project
git switch develop

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Configuración

StockFlow reconoce estas variables de entorno:

| Variable | Propósito |
| --- | --- |
| `STOCKFLOW_SECRET_KEY` | Firma la sesión de Flask. El valor por defecto sirve únicamente para desarrollo local. En cualquier entorno compartido debe configurarse un secreto propio. |
| `STOCKFLOW_DATABASE` | Permite elegir la ruta de la base SQLite. Si se omite, usa `database/stockflow.db`. |

No se requiere `.env`. Ejemplo en PowerShell:

```powershell
$env:STOCKFLOW_SECRET_KEY="cambiar-por-un-secreto-local"
$env:STOCKFLOW_DATABASE="$PWD\database\stockflow.db"
```

En Linux o macOS:

```bash
export STOCKFLOW_SECRET_KEY="cambiar-por-un-secreto-local"
export STOCKFLOW_DATABASE="$PWD/database/stockflow.db"
```

Cuando la ruta configurada no existe, `create_app()` crea las carpetas necesarias y genera automáticamente las nueve tablas desde `database/schema.sql`. Esto crea el esquema, pero no usuarios reales.

## Datos de demostración opcionales

El seed es una herramienta **SOLO DEMO / DESARROLLO LOCAL**. No se ejecuta al iniciar StockFlow y no modifica `database/stockflow.db` por defecto.

Crear la base separada `database/stockflow_demo.db`:

```powershell
python scripts/seed_demo.py
```

La base contiene un comercio activo, dos categorías, cuatro productos con distintos estados de stock/publicación, un ADMIN y un VENDEDOR. Comienza sin Caja abierta para poder demostrar ese paso manualmente.

Credenciales exclusivas de la demo:

```text
ADMIN
admin@stockflow.demo
StockFlow123!

VENDEDOR
vendedor@stockflow.demo
StockFlow123!
```

Las contraseñas se almacenan con hash. Estas credenciales conocidas no deben reutilizarse fuera de la demo local.

El seed rechaza sobrescribir una base existente. Para recrearla de forma explícita:

```powershell
python scripts/seed_demo.py --reset
```

También puede elegirse otra ruta:

```powershell
python scripts/seed_demo.py --database ".\database\mi_demo.db"
```

Los archivos `database/*.db`, `*.sqlite` y `*.sqlite3` están ignorados por Git.

## Ejecución

### Base local normal

```powershell
python app.py
```

### Base demo en Windows PowerShell

```powershell
$env:STOCKFLOW_DATABASE=(Resolve-Path ".\database\stockflow_demo.db").Path
$env:STOCKFLOW_SECRET_KEY="secreto-local-para-demo"
python app.py
```

### Base demo en Linux o macOS

```bash
export STOCKFLOW_DATABASE="$PWD/database/stockflow_demo.db"
export STOCKFLOW_SECRET_KEY="secreto-local-para-demo"
python app.py
```

`python app.py` inicia el servidor de desarrollo de Flask con debug para uso local. Abrir:

- aplicación y Catálogo: `http://127.0.0.1:5000/`;
- login interno: `http://127.0.0.1:5000/login`;
- selector de Catálogos: `http://127.0.0.1:5000/catalogo`;
- estado de la aplicación: `http://127.0.0.1:5000/health`.

La raíz redirige al Catálogo público. Después del login, cada usuario accede al Dashboard correspondiente a su rol.

## Pruebas

Con el entorno virtual activo:

```powershell
python -m pytest -q
```

La suite final del Issue #16 obtuvo `296 passed`. Incluye cobertura de base de datos, autenticación, permisos, Productos, Categorías, Inventario, Caja, Ventas, POS, Dashboard, Estadísticas, Catálogo, seed demo, integración cross-module, escenarios negativos, rollback, aislamiento entre comercios, navegación y presentación local de timestamps.

Compilación adicional usada para la revisión:

```powershell
python -m compileall -q app.py database routes services scripts tests utils
```

El registro del alcance automatizado y la checklist visual están en `docs/TESTING_MVP.md`.

## Endpoint de salud

`GET /health` no requiere autenticación y responde:

```json
{
  "application": "StockFlow",
  "status": "ok"
}
```

Este endpoint confirma que Flask responde; no reemplaza las pruebas funcionales ni es un sistema de monitoreo productivo.

## Estrategia de ramas

```text
main
└── develop
    ├── feature/<funcionalidad>
    ├── fix/<corrección>
    ├── test/<integración>
    └── docs/<documentación>
```

- `main`: versiones revisadas y presentables;
- `develop`: integración del trabajo aprobado;
- `feature/*`: módulos o capacidades funcionales;
- `fix/*`: correcciones puntuales;
- `test/*`: pruebas e integración;
- `docs/*`: documentación viva.

Los cambios se revisan mediante Pull Request hacia `develop`. La integración técnica se incorporó mediante el PR #31, el QA visual y sus correcciones mediante el PR #32, y el cierre documental mediante el PR #33. El Issue #16 está cerrado como `completed`. El PR #35 sincronizó el README con el QA final y la promoción revisada de `develop → main` se completó mediante el PR #34.

## Estado actual

El MVP académico funcional fue integrado en `main` mediante el PR #34, con commit de merge `84b0932c892eed24369321fa8ae11623ca7bd8be`. La última ejecución local previa a la promoción registró `296 passed`; la validación humana fue aprobada tanto en desktop como en mobile con viewport `390×844`, y la checklist visual quedó completada 16/16. INC-01, INC-02 e INC-03 están resueltas.

El PR #34 `develop → main` fue aprobado e integrado el 08/10/2026. El PR #35, con la actualización documental previa de QA, también fue integrado. La versión publicada en `main` mantiene el mismo contenido funcional que el candidato validado.

StockFlow sigue siendo un **MVP/demo académico funcional**, no una solución comercial lista para producción.

## Equipo y metodología

| Integrante | Responsabilidad principal |
| --- | --- |
| Axel Sosa | Desarrollo e integración |
| Robert Huyhua | Análisis y documentación |
| Dilan Amara | Testing y calidad |
| Natalia Benitez | UX/UI |

El equipo utiliza Scrum adaptado al proyecto escolar: Issues para el backlog, ramas por trabajo, commits convencionales, Pull Requests hacia `develop` y promoción revisada hacia `main`.
