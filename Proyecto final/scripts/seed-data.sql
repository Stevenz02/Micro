-- Datos de prueba: departamentos de la organización.
--
-- Se aplican sobre la base de Departamentos (fuente de verdad de los departamentos):
--
--   docker compose exec -T database-departamentos sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < scripts/seed-data.sql
--
-- En PowerShell:
--   Get-Content scripts\seed-data.sql | docker compose exec -T database-departamentos sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
--
-- Los empleados NO se siembran por SQL: deben crearse por la API (POST /empleados) para que se
-- publique empleado.creado y se generen la cuenta, el perfil y la notificación. El README trae
-- los ejemplos con curl.
INSERT INTO departamentos (id, nombre, descripcion) VALUES
    ('IT',   'Tecnología',        'Desarrollo, infraestructura y soporte'),
    ('RRHH', 'Recursos Humanos',  'Gestión del talento y bienestar'),
    ('FIN',  'Finanzas',          'Contabilidad, tesorería y presupuesto'),
    ('OPS',  'Operaciones',       'Operación y atención del servicio'),
    ('COM',  'Comercial',         'Ventas y relación con clientes')
ON CONFLICT (id) DO NOTHING;
