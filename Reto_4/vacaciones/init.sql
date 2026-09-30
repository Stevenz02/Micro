CREATE TABLE vacaciones (
    id TEXT PRIMARY KEY,
    empleado_id TEXT NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    estado TEXT NOT NULL CHECK (estado IN ('PROGRAMADA','EN_CURSO','FINALIZADA','CANCELADA')),
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (fecha_fin > fecha_inicio)
);
CREATE INDEX vacaciones_empleado_periodo_idx ON vacaciones(empleado_id, fecha_inicio, fecha_fin);

CREATE TABLE empleados_replica (
    empleado_id TEXT PRIMARY KEY,
    estado TEXT NOT NULL CHECK (estado IN ('ACTIVO','RETIRADO')),
    email TEXT,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE eventos_procesados (
    id UUID PRIMARY KEY,
    procesado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
