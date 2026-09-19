-- Solo se ejecuta con volumen vacío. Con datos existentes, aplicar una
-- migración ALTER TABLE revisada y respaldada; no borrar datos para migrar.
CREATE TABLE empleados (
    id              TEXT PRIMARY KEY CHECK (length(btrim(id)) > 0),
    nombre          TEXT NOT NULL,
    apellido        TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE CHECK (email = lower(email)),
    numero_empleado TEXT NOT NULL UNIQUE,
    cargo           TEXT NOT NULL,
    area            TEXT NOT NULL,
    departamento_id TEXT NOT NULL,
    fecha_ingreso   DATE NOT NULL,
    estado          TEXT NOT NULL DEFAULT 'ACTIVO' CHECK (estado = 'ACTIVO')
);
-- No hay FK entre bases: departamentos se valida exclusivamente por HTTP.
