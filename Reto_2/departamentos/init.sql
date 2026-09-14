-- Se ejecuta SOLO la primera vez que el volumen está vacío.

CREATE TABLE IF NOT EXISTS departamentos (
    id          VARCHAR(20) PRIMARY KEY,
    nombre      VARCHAR(100) NOT NULL,
    descripcion VARCHAR(255)
);