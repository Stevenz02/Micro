-- Inicialización exclusiva de volúmenes vacíos.
CREATE TABLE departamentos (
    id          TEXT PRIMARY KEY CHECK (length(btrim(id)) > 0),
    nombre      TEXT NOT NULL CHECK (length(btrim(nombre)) > 0),
    descripcion TEXT NOT NULL CHECK (length(btrim(descripcion)) > 0)
);
