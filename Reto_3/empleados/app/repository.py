import psycopg
from psycopg.rows import dict_row

from .models import Empleado


COLUMNS = '''id, nombre, apellido, email, numero_empleado AS "numeroEmpleado",
             cargo, area, departamento_id AS "departamentoId",
             fecha_ingreso AS "fechaIngreso", estado'''


class Repository:
    def __init__(self, config):
        self.config = config

    def _query(self, statement, params=(), *, many=False):
        # El contexto confirma la transacción o hace rollback, y cierra la conexión.
        with psycopg.connect(**self.config, row_factory=dict_row) as conn:
            cursor = conn.execute(statement, params)
            return cursor.fetchall() if many else cursor.fetchone()

    def ready(self):
        self._query("SELECT id FROM empleados LIMIT 1")

    def existe_email(self, email):
        return self._query("SELECT id FROM empleados WHERE email = %s", (email,)) is not None

    def existe_numero(self, numero):
        return self._query("SELECT id FROM empleados WHERE numero_empleado = %s", (numero,)) is not None

    def obtener(self, empleado_id):
        row = self._query(f"SELECT {COLUMNS} FROM empleados WHERE id = %s", (empleado_id,))
        return Empleado(**row) if row else None

    def listar(self):
        return [Empleado(**row) for row in self._query(
            f"SELECT {COLUMNS} FROM empleados ORDER BY id", many=True
        )]

    def crear(self, empleado):
        row = self._query(
            f'''INSERT INTO empleados
                (id, nombre, apellido, email, numero_empleado, cargo, area,
                 departamento_id, fecha_ingreso, estado)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING {COLUMNS}''',
            (empleado.id, empleado.nombre, empleado.apellido, empleado.email,
             empleado.numeroEmpleado, empleado.cargo, empleado.area,
             empleado.departamentoId, empleado.fechaIngreso, "ACTIVO"),
        )
        return Empleado(**row)
