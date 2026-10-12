"""Integración con PostgreSQL efímero; no usa servicios de negocio ni RabbitMQ."""

from pathlib import Path

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from Reto_1.app.models import EMPLEADO_EJEMPLO
from Reto_4.empleados.app.models import Empleado
from Reto_4.empleados.app.repository import Repository


@pytest.mark.integration
def test_postgres_persistence_uniqueness_and_logical_retirement():
    schema = Path(__file__).resolve().parents[1] / "empleados" / "init.sql"
    with PostgresContainer("postgres:16-alpine") as postgres:
        config = {
            "host": postgres.get_container_host_ip(),
            "port": int(postgres.get_exposed_port(5432)),
            "dbname": postgres.dbname,
            "user": postgres.username,
            "password": postgres.password,
        }
        with psycopg.connect(**config) as connection:
            connection.execute(schema.read_text(encoding="utf-8"))
        repo = Repository(config)
        original = Empleado(**EMPLEADO_EJEMPLO)
        assert repo.crear(original).id == "E001"
        assert repo.obtener("E001").email == original.email
        assert repo.existe_email(original.email)
        assert repo.existe_numero(original.numeroEmpleado)
        with pytest.raises(psycopg.errors.UniqueViolation):
            repo.crear(original.model_copy(update={"id": "E002", "numeroEmpleado": "NUM-2"}))
        with pytest.raises(psycopg.errors.UniqueViolation):
            repo.crear(original.model_copy(update={"id": "E003", "email": "other@example.test"}))
        retired = repo.retirar("E001", "RENUNCIA")
        assert retired.estado == "RETIRADO" and retired.fechaRetiro is not None
        assert repo.obtener("E001").fechaRetiro == retired.fechaRetiro
        assert [e.id for e in repo.listar(estado="RETIRADO")] == ["E001"]
        assert repo.retirar("E001", "OTRO") is None
        with psycopg.connect(**config) as connection:
            row = connection.execute("SELECT motivo_retiro FROM empleados WHERE id='E001'").fetchone()
            assert row == ("RENUNCIA",)
