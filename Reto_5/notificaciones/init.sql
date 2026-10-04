CREATE TABLE notificaciones (
    id UUID PRIMARY KEY,
    tipo TEXT NOT NULL CHECK (tipo IN ('ALTA', 'RETIRO', 'BIENVENIDA', 'DESVINCULACION', 'VACACIONES', 'SEGURIDAD', 'CUENTA')),
    destinatario TEXT NOT NULL,
    mensaje TEXT NOT NULL,
    fecha_envio TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    empleado_id TEXT NULL,
    token_entrega TEXT NULL,
    token_expira_en TIMESTAMPTZ NULL
);
CREATE INDEX notificaciones_empleado_idx ON notificaciones(empleado_id, fecha_envio);

CREATE TABLE eventos_procesados (
    id UUID PRIMARY KEY,
    procesado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
