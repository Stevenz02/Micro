-- Se ejecuta SOLO la primera vez que el volumen está vacío.
-- Si necesitan cambiar el esquema después, hay que:
--   docker compose down -v   (borra el volumen y TODOS los datos)
--   docker compose up --build

CREATE TABLE IF NOT EXISTS empleados (
    id              VARCHAR(20) PRIMARY KEY,
    nombre          VARCHAR(100) NOT NULL,
    apellido        VARCHAR(100) NOT NULL,
    email           VARCHAR(150) NOT NULL UNIQUE,
    numero_empleado VARCHAR(50)  NOT NULL UNIQUE,
    cargo           VARCHAR(100) NOT NULL,
    area            VARCHAR(100) NOT NULL,
    departamento_id VARCHAR(20)  NOT NULL,
    fecha_ingreso   DATE         NOT NULL,
    estado          VARCHAR(20)  NOT NULL DEFAULT 'ACTIVO'
);

-- La restricción UNIQUE de email y numero_empleado es la garantía real
-- contra condiciones de carrera (dos peticiones simultáneas con el mismo
-- dato). La validación en el código (consultar antes de insertar) solo
-- da un mensaje de error más amigable; el UNIQUE es quien evita el
-- duplicado si ambas llegan al mismo tiempo.