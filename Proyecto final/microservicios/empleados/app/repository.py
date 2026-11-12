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
        # Una sola transacción: el primer ALTER bloquea la tabla, así dos réplicas que arrancan
        # a la vez migran en serie en lugar de pisarse.
        with psycopg.connect(**self.config) as conn:
            conn.execute("ALTER TABLE empleados ADD COLUMN IF NOT EXISTS fecha_retiro TIMESTAMPTZ NULL")
            conn.execute("ALTER TABLE empleados ADD COLUMN IF NOT EXISTS motivo_retiro TEXT NULL")
            conn.execute("ALTER TABLE empleados DROP CONSTRAINT IF EXISTS empleados_estado_check")
            conn.execute(
                "ALTER TABLE empleados ADD CONSTRAINT empleados_estado_check "
                "CHECK (estado IN ('ACTIVO', 'EN_VACACIONES', 'PENDIENTE', 'RECHAZADO', 'RETIRADO'))"
            )
            # Deduplicación de eventos consumidos (campo id del envelope)
            conn.execute(
                "CREATE TABLE IF NOT EXISTS eventos_procesados ("
                "id UUID PRIMARY KEY, procesado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)"
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
            f"UPDATE empleados SET estado = %s WHERE id = %s AND estado = 'PENDIENTE' RETURNING {COLUMNS}",
            (estado, empleado_id),
        )
        return Empleado(**row) if row else None

    def aplicar_vacaciones(self, event_id, empleado_id, iniciadas):
        """Aplica vacaciones.iniciadas/finalizadas de forma idempotente.

        El id del evento y el cambio de estado se confirman en la misma transacción, de modo que
        una reentrega (o la otra réplica) no repite el efecto. Devuelve (evento_nuevo, empleado).
        """
        self.ensure_schema()
        origen, destino = ("ACTIVO", "EN_VACACIONES") if iniciadas else ("EN_VACACIONES", "ACTIVO")
        with psycopg.connect(**self.config, row_factory=dict_row) as conn:
            nuevo = conn.execute(
                "INSERT INTO eventos_procesados (id) VALUES (%s) ON CONFLICT DO NOTHING RETURNING id",
                (event_id,),
            ).fetchone()
            if nuevo is None:
                return False, None
            row = conn.execute(
                f"UPDATE empleados SET estado = %s WHERE id = %s AND estado = %s RETURNING {COLUMNS}",
                (destino, empleado_id, origen),
            ).fetchone()
            return True, Empleado(**row) if row else None

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

    def retirar(self, empleado_id, motivo):
        row = self._query(
            f'''UPDATE empleados SET estado = 'RETIRADO', fecha_retiro = CURRENT_TIMESTAMP,
                motivo_retiro = %s
                WHERE id = %s AND estado <> 'RETIRADO' RETURNING {COLUMNS}''',
            (motivo, empleado_id),
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
