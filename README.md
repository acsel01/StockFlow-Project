# StockFlow

Sistema web de gestión comercial, inventario y consulta pública de disponibilidad para pequeños comercios.

## Descripción

StockFlow integra en una sola aplicación las tareas diarias de un kiosco, almacén, despensa o comercio pequeño: productos, inventario, ventas, caja y estadísticas. La misma información de stock alimenta un catálogo público para que los clientes puedan consultar productos y disponibilidad antes de acercarse al local.

El proyecto se desarrolla como trabajo anual de Programación 2026.

## Objetivo

Facilitar la gestión operativa de pequeños comercios, reducir errores de stock y aprovechar la información del inventario para ofrecer una consulta pública simple y actualizada.

## Funcionalidades del MVP

Las siguientes funcionalidades conforman el alcance planificado para la primera versión:

- Inicio de sesión y permisos para administradores y vendedores.
- Dashboard con información resumida del comercio.
- Alta, edición, consulta y baja lógica de productos.
- Categorías, precios, código de barras y visibilidad pública.
- Inventario integrado y registro de movimientos de stock.
- Punto de venta con descuento automático de existencias.
- Apertura, seguimiento y cierre básico de caja.
- Historial y detalle de ventas.
- Estadísticas de ventas, total vendido e inventario.
- Catálogo público con estados de disponibilidad.
- Diseño adaptable a computadora y celular.

No forman parte del MVP la facturación fiscal, los pagos en línea, los proveedores, las múltiples sucursales ni la geolocalización avanzada.

## Equipo y responsabilidades

La planificación y las decisiones se realizan en equipo. Para organizar el trabajo se definió esta asignación operativa inicial:

| Integrante | Responsabilidad principal |
| --- | --- |
| Axel Sosa | Desarrollo e integración |
| Robert Huyhua | Análisis y documentación |
| Dilan Amara | Testing y calidad |
| Natalia Benitez | UX/UI |

## Roles de usuario

- **ADMIN:** acceso completo a dashboard, punto de venta, productos, inventario, caja, ventas, estadísticas y catálogo.
- **VENDEDOR:** acceso operativo a punto de venta, consulta de inventario, caja y ventas autorizadas.
- **CLIENTE:** acceso sin autenticación al catálogo público.

La autenticación y la aplicación efectiva de estos permisos forman parte del backlog de desarrollo.

## Tecnologías

| Capa | Tecnología | Uso |
| --- | --- | --- |
| Frontend | HTML5, CSS3 y JavaScript | Interfaz y comportamiento |
| UI | Bootstrap + CSS propio | Componentes adaptables e identidad visual |
| Backend | Python + Flask | Rutas, sesiones, validaciones y lógica |
| Base de datos | SQLite | Persistencia local del MVP |
| Gráficos | Chart.js | Dashboard y estadísticas |
| Testing | pytest | Pruebas automatizadas |

## Arquitectura

StockFlow utiliza una aplicación web monolítica modular:

```text
Navegador
   │
   ▼
HTML + CSS + JavaScript + Bootstrap
   │
   ▼
Flask / Routes
   │
   ▼
Services / Lógica de negocio
   │
   ▼
SQLite
```

Las rutas reciben las peticiones y delegan la lógica de negocio a los servicios. La operación **Confirmar venta** deberá ejecutarse dentro de una transacción: crear la venta y sus detalles, descontar stock y registrar los movimientos; si una parte falla, se revierte toda la operación.

El esquema inicial contempla nueve entidades: Comercio, Usuario, Categoría, Producto, Inventario, MovimientoInventario, Caja, Venta y DetalleVenta.

## Estructura del proyecto

```text
StockFlow-Project/
├── app.py
├── requirements.txt
├── README.md
├── database/
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
│   └── estadisticas_service.py
├── templates/
│   ├── base.html
│   ├── productos/
│   ├── inventario/
│   ├── ventas/
│   ├── caja/
│   ├── estadisticas/
│   └── catalogo/
├── static/
│   ├── css/
│   ├── js/
│   └── img/
├── tests/
└── utils/
```

## Instalación y ejecución

### Requisitos

- Python 3.10 o superior.
- Git.

### Pasos

1. Clonar el repositorio y entrar a la carpeta:

   ```bash
   git clone https://github.com/acsel01/StockFlow-Project.git
   cd StockFlow-Project
   git checkout develop
   ```

2. Crear y activar un entorno virtual:

   En Windows:

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   En Linux o macOS:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Instalar dependencias:

   ```bash
   pip install -r requirements.txt
   ```

4. Ejecutar la aplicación:

   ```bash
   python app.py
   ```

5. Abrir `http://127.0.0.1:5000`.

La primera ejecución crea automáticamente `database/stockflow.db` usando `database/schema.sql`. El archivo local de base de datos no se versiona.

### Pruebas

```bash
pytest
```

También está disponible el endpoint `/health` para comprobar que la aplicación responde.

## Estado del proyecto

- **Etapas 1 y 2:** completadas.
- **Etapa 3 — Investigación de usuarios y mercado:** en progreso; continúa abierta porque requiere evidencia real de encuestas y entrevistas.
- **Etapas 4 a 14:** documentación funcional, UX/UI, modelo de datos y arquitectura elaborados.
- **Etapa 15 — GitHub y control de versiones:** repositorio y base técnica en preparación para el desarrollo.
- **Implementación:** estructura inicial creada; los módulos funcionales todavía se encuentran en el backlog.

Este estado no declara completada la Etapa 3 ni funcionalidades que todavía no fueron implementadas.

## Metodología de trabajo

El equipo utiliza Scrum adaptado al proyecto escolar:

1. Los requerimientos se registran como Issues y conforman el backlog.
2. Las tareas se priorizan y asignan a un sprint.
3. Cada funcionalidad se desarrolla en una rama `feature/...`.
4. Los cambios se revisan mediante Pull Request hacia `develop`.
5. Las pruebas e integración se realizan antes de promover una versión estable a `main`.
6. Al finalizar el sprint se realiza review y retrospectiva.

Los Issues deben indicar objetivo, alcance y criterios de finalización. El tablero de tareas refleja los estados Pendiente, En progreso, En prueba y Terminado cuando se configure o actualice en GitHub Projects.

## Estrategia de ramas

```text
main
└── develop
    ├── feature/autenticacion
    ├── feature/productos
    ├── feature/inventario
    ├── feature/punto-venta
    └── feature/...
```

- **`main`:** versiones estables y presentables.
- **`develop`:** integración del trabajo del sprint.
- **`feature/<nombre>`:** desarrollo aislado de una funcionalidad.
- **`fix/<nombre>`:** correcciones puntuales.
- **`docs/<nombre>`:** cambios exclusivamente documentales.

Las ramas de funcionalidad se crean cuando comienza la tarea correspondiente; no se mantienen ramas vacías como evidencia.

## Convención de commits

Se utiliza una convención breve basada en Conventional Commits:

| Tipo | Uso | Ejemplo |
| --- | --- | --- |
| `feat` | Nueva funcionalidad | `feat: add product management` |
| `fix` | Corrección de un error | `fix: prevent negative stock` |
| `docs` | Documentación | `docs: update project README` |
| `style` | Cambios visuales sin alterar lógica | `style: implement dashboard layout` |
| `test` | Pruebas | `test: cover sale transaction` |
| `refactor` | Reorganización interna | `refactor: separate inventory service` |
| `chore` | Configuración o mantenimiento | `chore: create initial Flask structure` |

Los mensajes se escriben en imperativo, describen un cambio concreto y evitan textos genéricos como “cambios” o “update”.
