PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS comercio (
    id_comercio INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(120) NOT NULL,
    direccion VARCHAR(180) NOT NULL,
    barrio VARCHAR(100),
    localidad VARCHAR(100),
    telefono VARCHAR(30),
    activo BOOLEAN NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usuario (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    id_comercio INTEGER NOT NULL,
    nombre VARCHAR(80) NOT NULL,
    apellido VARCHAR(80),
    email VARCHAR(160) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol VARCHAR(20) NOT NULL CHECK (rol IN ('ADMIN', 'VENDEDOR')),
    activo BOOLEAN NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_comercio) REFERENCES comercio(id_comercio)
);

CREATE TABLE IF NOT EXISTS categoria (
    id_categoria INTEGER PRIMARY KEY AUTOINCREMENT,
    id_comercio INTEGER NOT NULL,
    nombre VARCHAR(80) NOT NULL,
    descripcion TEXT,
    activa BOOLEAN NOT NULL DEFAULT 1 CHECK (activa IN (0, 1)),
    UNIQUE (id_comercio, nombre),
    FOREIGN KEY (id_comercio) REFERENCES comercio(id_comercio)
);

CREATE TABLE IF NOT EXISTS producto (
    id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
    id_comercio INTEGER NOT NULL,
    id_categoria INTEGER NOT NULL,
    nombre VARCHAR(140) NOT NULL,
    descripcion TEXT,
    codigo_barras VARCHAR(60),
    precio_compra DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK (precio_compra >= 0),
    precio_venta DECIMAL(10,2) NOT NULL CHECK (precio_venta >= 0),
    imagen_url VARCHAR(255),
    visible_catalogo BOOLEAN NOT NULL DEFAULT 0 CHECK (visible_catalogo IN (0, 1)),
    activo BOOLEAN NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (id_comercio, codigo_barras),
    FOREIGN KEY (id_comercio) REFERENCES comercio(id_comercio),
    FOREIGN KEY (id_categoria) REFERENCES categoria(id_categoria)
);

CREATE TABLE IF NOT EXISTS inventario (
    id_inventario INTEGER PRIMARY KEY AUTOINCREMENT,
    id_producto INTEGER NOT NULL UNIQUE,
    stock_actual INTEGER NOT NULL DEFAULT 0 CHECK (stock_actual >= 0),
    stock_minimo INTEGER NOT NULL DEFAULT 0 CHECK (stock_minimo >= 0),
    ultima_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_producto) REFERENCES producto(id_producto)
);

CREATE TABLE IF NOT EXISTS caja (
    id_caja INTEGER PRIMARY KEY AUTOINCREMENT,
    id_comercio INTEGER NOT NULL,
    id_usuario_apertura INTEGER NOT NULL,
    id_usuario_cierre INTEGER,
    fecha_apertura DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_cierre DATETIME,
    monto_inicial DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK (monto_inicial >= 0),
    efectivo_contado DECIMAL(10,2) CHECK (efectivo_contado >= 0),
    estado VARCHAR(15) NOT NULL DEFAULT 'ABIERTA'
        CHECK (estado IN ('ABIERTA', 'CERRADA')),
    FOREIGN KEY (id_comercio) REFERENCES comercio(id_comercio),
    FOREIGN KEY (id_usuario_apertura) REFERENCES usuario(id_usuario),
    FOREIGN KEY (id_usuario_cierre) REFERENCES usuario(id_usuario)
);

CREATE TABLE IF NOT EXISTS venta (
    id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
    id_caja INTEGER NOT NULL,
    id_usuario INTEGER NOT NULL,
    fecha_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    subtotal DECIMAL(10,2) NOT NULL CHECK (subtotal >= 0),
    descuento DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK (descuento >= 0),
    total DECIMAL(10,2) NOT NULL CHECK (total >= 0),
    medio_pago VARCHAR(20) NOT NULL
        CHECK (medio_pago IN ('EFECTIVO', 'DEBITO', 'CREDITO', 'TRANSFERENCIA')),
    dinero_recibido DECIMAL(10,2) CHECK (dinero_recibido >= 0),
    vuelto DECIMAL(10,2) CHECK (vuelto >= 0),
    estado VARCHAR(20) NOT NULL DEFAULT 'COMPLETADA'
        CHECK (estado IN ('COMPLETADA')),
    observaciones TEXT,
    FOREIGN KEY (id_caja) REFERENCES caja(id_caja),
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
);

CREATE TABLE IF NOT EXISTS detalle_venta (
    id_detalle_venta INTEGER PRIMARY KEY AUTOINCREMENT,
    id_venta INTEGER NOT NULL,
    id_producto INTEGER NOT NULL,
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario DECIMAL(10,2) NOT NULL CHECK (precio_unitario >= 0),
    subtotal DECIMAL(10,2) NOT NULL CHECK (subtotal >= 0),
    FOREIGN KEY (id_venta) REFERENCES venta(id_venta),
    FOREIGN KEY (id_producto) REFERENCES producto(id_producto)
);

CREATE TABLE IF NOT EXISTS movimiento_inventario (
    id_movimiento INTEGER PRIMARY KEY AUTOINCREMENT,
    id_inventario INTEGER NOT NULL,
    id_usuario INTEGER NOT NULL,
    id_venta INTEGER,
    tipo VARCHAR(30) NOT NULL CHECK (
        tipo IN (
            'VENTA',
            'REPOSICION',
            'CORRECCION',
            'PERDIDA',
            'CONTEO_FISICO',
            'OTRO'
        )
    ),
    cantidad_delta INTEGER NOT NULL CHECK (cantidad_delta <> 0),
    motivo TEXT,
    stock_anterior INTEGER NOT NULL CHECK (stock_anterior >= 0),
    stock_resultante INTEGER NOT NULL CHECK (stock_resultante >= 0),
    fecha_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_inventario) REFERENCES inventario(id_inventario),
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario),
    FOREIGN KEY (id_venta) REFERENCES venta(id_venta)
);

CREATE INDEX IF NOT EXISTS idx_producto_nombre
    ON producto(nombre);

CREATE INDEX IF NOT EXISTS idx_producto_codigo_barras
    ON producto(id_comercio, codigo_barras);

CREATE INDEX IF NOT EXISTS idx_venta_fecha_hora
    ON venta(fecha_hora);

CREATE INDEX IF NOT EXISTS idx_venta_caja
    ON venta(id_caja);

CREATE INDEX IF NOT EXISTS idx_movimiento_inventario
    ON movimiento_inventario(id_inventario);

CREATE INDEX IF NOT EXISTS idx_movimiento_venta
    ON movimiento_inventario(id_venta);
