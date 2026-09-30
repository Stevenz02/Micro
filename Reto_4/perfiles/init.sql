CREATE TABLE perfiles (
    id UUID PRIMARY KEY,
    empleado_id TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    apellido TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL,
    cargo TEXT NOT NULL DEFAULT '',
    area TEXT NOT NULL DEFAULT '',
    departamento_id TEXT NOT NULL DEFAULT '',
    telefono TEXT NOT NULL DEFAULT '',
    direccion TEXT NOT NULL DEFAULT '',
    ciudad TEXT NOT NULL DEFAULT '',
    biografia TEXT NOT NULL DEFAULT '',
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    archivado BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE eventos_procesados (
    id UUID PRIMARY KEY,
    procesado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
