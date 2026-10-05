PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS comercio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    direccion TEXT,
    horario TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usuario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comercio_id INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('ADMIN', 'VENDEDOR')),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (comercio_id) REFERENCES comercio(id)
);

CREATE TABLE IF NOT EXISTS categoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comercio_id INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    UNIQUE (comercio_id, nombre),
    FOREIGN KEY (comercio_id) REFERENCES comercio(id)
);

CREATE TABLE IF NOT EXISTS producto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comercio_id INTEGER NOT NULL,
    categoria_id INTEGER,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    codigo_barra TEXT UNIQUE,
    precio_compra REAL NOT NULL DEFAULT 0 CHECK (precio_compra >= 0),
    precio_venta REAL NOT NULL CHECK (precio_venta >= 0),
    visible_catalogo INTEGER NOT NULL DEFAULT 1 CHECK (visible_catalogo IN (0, 1)),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (comercio_id) REFERENCES comercio(id),
    FOREIGN KEY (categoria_id) REFERENCES categoria(id)
);

CREATE TABLE IF NOT EXISTS inventario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL UNIQUE,
    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    stock_minimo INTEGER NOT NULL DEFAULT 0 CHECK (stock_minimo >= 0),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (producto_id) REFERENCES producto(id)
);

CREATE TABLE IF NOT EXISTS caja (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comercio_id INTEGER NOT NULL,
    usuario_apertura_id INTEGER NOT NULL,
    fecha_apertura TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_cierre TEXT,
    monto_inicial REAL NOT NULL DEFAULT 0 CHECK (monto_inicial >= 0),
    monto_final REAL,
    estado TEXT NOT NULL DEFAULT 'ABIERTA' CHECK (estado IN ('ABIERTA', 'CERRADA')),
    FOREIGN KEY (comercio_id) REFERENCES comercio(id),
    FOREIGN KEY (usuario_apertura_id) REFERENCES usuario(id)
);

CREATE TABLE IF NOT EXISTS venta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comercio_id INTEGER NOT NULL,
    caja_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total REAL NOT NULL CHECK (total >= 0),
    medio_pago TEXT NOT NULL DEFAULT 'EFECTIVO',
    estado TEXT NOT NULL DEFAULT 'CONFIRMADA' CHECK (estado IN ('CONFIRMADA', 'ANULADA')),
    FOREIGN KEY (comercio_id) REFERENCES comercio(id),
    FOREIGN KEY (caja_id) REFERENCES caja(id),
    FOREIGN KEY (usuario_id) REFERENCES usuario(id)
);

CREATE TABLE IF NOT EXISTS detalle_venta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario REAL NOT NULL CHECK (precio_unitario >= 0),
    subtotal REAL NOT NULL CHECK (subtotal >= 0),
    FOREIGN KEY (venta_id) REFERENCES venta(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES producto(id)
);

CREATE TABLE IF NOT EXISTS movimiento_inventario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    venta_id INTEGER,
    usuario_id INTEGER NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('ENTRADA', 'SALIDA', 'AJUSTE')),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    stock_anterior INTEGER NOT NULL CHECK (stock_anterior >= 0),
    stock_posterior INTEGER NOT NULL CHECK (stock_posterior >= 0),
    motivo TEXT,
    fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (producto_id) REFERENCES producto(id),
    FOREIGN KEY (venta_id) REFERENCES venta(id),
    FOREIGN KEY (usuario_id) REFERENCES usuario(id)
);

CREATE INDEX IF NOT EXISTS idx_producto_nombre ON producto(nombre);
CREATE INDEX IF NOT EXISTS idx_venta_fecha ON venta(fecha);
CREATE INDEX IF NOT EXISTS idx_movimiento_producto ON movimiento_inventario(producto_id);
