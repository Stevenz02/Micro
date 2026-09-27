import psycopg
from psycopg.rows import dict_row

from .models import Empleado


COLUMNS = '''id, nombre, apellido, email, numero_empleado AS "numeroEmpleado",
             cargo, area, departamento_id AS "departamentoId",
             fecha_ingreso AS "fechaIngreso", estado,
             fecha_retiro AS "fechaRetiro"'''


class Repository:
    def __init__(self, config):
        self.config = config
        self._schema_ready = False

    def _query(self, statement, params=(), *, many=False):
        # El contexto confirma la transacción o hace rollback, y cierra la conexión.
        with psycopg.connect(**self.config, row_factory=dict_row) as conn:
            cursor = conn.execute(statement, params)
            return cursor.fetchall() if many else cursor.fetchone()

    def _execute(self, statement, params=()):
        with psycopg.connect(**self.config) as conn:
            conn.execute(statement, params)

    def ensure_schema(self):
        if self._schema_ready:
            return
        self._execute("ALTER TABLE empleados ADD COLUMN IF NOT EXISTS fecha_retiro TIMESTAMPTZ NULL")
        self._execute("ALTER TABLE empleados DROP CONSTRAINT IF EXISTS empleados_estado_check")
        self._execute(
            "ALTER TABLE empleados ADD CONSTRAINT empleados_estado_check "
            "CHECK (estado IN ('ACTIVO', 'PENDIENTE', 'RECHAZADO', 'RETIRADO'))"
        )
        self._schema_ready = True

    def ready(self):
        self.ensure_schema()
        self._query("SELECT id FROM empleados LIMIT 1")

    def existe_email(self, email, excluir_id=None):
        if excluir_id is None:
            return self._query("SELECT id FROM empleados WHERE email = %s", (email,)) is not None
        return self._query("SELECT id FROM empleados WHERE email = %s AND id <> %s", (email, excluir_id)) is not None

    def existe_numero(self, numero, excluir_id=None):
        if excluir_id is None:
            return self._query("SELECT id FROM empleados WHERE numero_empleado = %s", (numero,)) is not None
        return self._query("SELECT id FROM empleados WHERE numero_empleado = %s AND id <> %s", (numero, excluir_id)) is not None

    def obtener(self, empleado_id):
        row = self._query(f"SELECT {COLUMNS} FROM empleados WHERE id = %s", (empleado_id,))
        return Empleado(**row) if row else None

    def listar(self, estado=None, desde=None, hasta=None):
        condiciones, params = [], []
        if estado is not None:
            condiciones.append("estado = %s")
            params.append(estado)
        if desde is not None:
            condiciones.append("fecha_retiro::date >= %s")
            params.append(desde)
        if hasta is not None:
            condiciones.append("fecha_retiro::date <= %s")
            params.append(hasta)
        where = f" WHERE {' AND '.join(condiciones)}" if condiciones else ""
        return [
            Empleado(**row)
            for row in self._query(f"SELECT {COLUMNS} FROM empleados{where} ORDER BY id", params, many=True)
        ]

    def listar_pendientes(self, limit=50):
        self.ensure_schema()
        return [
            Empleado(**row) for row in self._query(
                f"SELECT {COLUMNS} FROM empleados WHERE estado = 'PENDIENTE' ORDER BY id LIMIT %s",
                (limit,),
                many=True,
            )
        ]

    def actualizar_estado(self, empleado_id, estado):
        self.ensure_schema()
        row = self._query(
            f"UPDATE empleados SET estado = %s WHERE id = %s RETURNING {COLUMNS}",
            (estado, empleado_id),
        )
        return Empleado(**row) if row else None

    def actualizar(self, empleado_id, cambios):
        row = self._query(
            f'''UPDATE empleados SET nombre = %s, apellido = %s, email = %s,
                numero_empleado = %s, cargo = %s, area = %s,
                departamento_id = %s, fecha_ingreso = %s
                WHERE id = %s AND estado <> 'RETIRADO'
                RETURNING {COLUMNS}''',
            (
                cambios.nombre, cambios.apellido, cambios.email, cambios.numeroEmpleado,
                cambios.cargo, cambios.area, cambios.departamentoId,
                cambios.fechaIngreso, empleado_id,
            ),
        )
        return Empleado(**row) if row else None

    def retirar(self, empleado_id):
        row = self._query(
            f'''UPDATE empleados SET estado = 'RETIRADO', fecha_retiro = CURRENT_TIMESTAMP
                WHERE id = %s AND estado <> 'RETIRADO' RETURNING {COLUMNS}''',
            (empleado_id,),
        )
        return Empleado(**row) if row else None

    def crear(self, empleado):
        self.ensure_schema()
        row = self._query(
            f'''INSERT INTO empleados
                (id, nombre, apellido, email, numero_empleado, cargo, area,
                 departamento_id, fecha_ingreso, estado, fecha_retiro)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING {COLUMNS}''',
            (empleado.id, empleado.nombre, empleado.apellido, empleado.email,
             empleado.numeroEmpleado, empleado.cargo, empleado.area,
             empleado.departamentoId, empleado.fechaIngreso, empleado.estado, empleado.fechaRetiro),
        )
        return Empleado(**row)
