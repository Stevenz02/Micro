from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


EMPLEADO_EJEMPLO = {
    "id": "E001",
    "nombre": "Juan",
    "apellido": "Pérez",
    "email": "juan.perez@empresa.com",
    "numeroEmpleado": "EMP-2026-001",
    "cargo": "Desarrollador Senior",
    "area": "Tecnología",
    "departamentoId": "IT",
    "fechaIngreso": "2026-02-10",
    "estado": "ACTIVO",
}


class Empleado(BaseModel):
    """Datos requeridos para registrar un empleado."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={"examples": [EMPLEADO_EJEMPLO]},
    )

    id: str = Field(
        min_length=1,
        description="Identificador único del empleado",
        examples=["E001"],
    )
    nombre: str = Field(
        min_length=1, description="Nombre del empleado", examples=["Juan"]
    )
    apellido: str = Field(
        min_length=1, description="Apellido del empleado", examples=["Pérez"]
    )
    email: str = Field(
        min_length=3,
        description="Correo electrónico corporativo",
        examples=["juan.perez@empresa.com"],
    )
    numeroEmpleado: str = Field(
        min_length=1,
        description="Número único asignado al empleado",
        examples=["EMP-2026-001"],
    )
    cargo: str = Field(
        min_length=1,
        description="Cargo actual del empleado",
        examples=["Desarrollador Senior"],
    )
    area: str = Field(
        min_length=1, description="Área organizacional", examples=["Tecnología"]
    )
    departamentoId: str = Field(
        min_length=1,
        description="Identificador textual del departamento",
        examples=["IT"],
    )
    fechaIngreso: date = Field(
        description="Fecha de ingreso del empleado", examples=["2026-02-10"]
    )
    estado: Literal["ACTIVO"] = Field(
        description="Estado actual del empleado. En este reto únicamente se admite ACTIVO",
        examples=["ACTIVO"],
    )

    @field_validator("email")
    @classmethod
    def validar_email(cls, valor: str) -> str:
        """Aplica una validación sencilla sin dependencias adicionales."""
        parte_local, separador, dominio = valor.rpartition("@")
        if not separador or not parte_local or "." not in dominio:
            raise ValueError("El email no tiene un formato válido")
        if dominio.startswith(".") or dominio.endswith("."):
            raise ValueError("El email no tiene un formato válido")
        return valor.lower()
