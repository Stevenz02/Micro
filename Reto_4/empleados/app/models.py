"""Modelos REST de empleados para Reto 4, sin definir contratos de eventos."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from Reto_1.app.models import EMPLEADO_EJEMPLO, Empleado as EmpleadoOriginal


class Empleado(EmpleadoOriginal):
    estado: Literal["ACTIVO", "PENDIENTE", "RECHAZADO", "RETIRADO"] = Field(
        default="ACTIVO",
        description="Estado actual del empleado",
        examples=["ACTIVO", "PENDIENTE", "RECHAZADO", "RETIRADO"],
    )
    fechaRetiro: datetime | None = Field(
        default=None,
        description="Instante UTC de la baja logica; solo existe para empleados RETIRADO",
    )


class EmpleadoActualizacion(BaseModel):
    """Campos de negocio editables; id, estado y fechaRetiro quedan protegidos."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    nombre: str = Field(min_length=1)
    apellido: str = Field(min_length=1)
    email: str = Field(min_length=3)
    numeroEmpleado: str = Field(min_length=1)
    cargo: str = Field(min_length=1)
    area: str = Field(min_length=1)
    departamentoId: str = Field(min_length=1)
    fechaIngreso: date

    @field_validator("email")
    @classmethod
    def validar_email(cls, valor: str) -> str:
        parte_local, separador, dominio = valor.rpartition("@")
        if not separador or not parte_local or "." not in dominio:
            raise ValueError("El email no tiene un formato valido")
        if dominio.startswith(".") or dominio.endswith("."):
            raise ValueError("El email no tiene un formato valido")
        return valor.lower()


__all__ = ["EMPLEADO_EJEMPLO", "Empleado", "EmpleadoActualizacion"]
