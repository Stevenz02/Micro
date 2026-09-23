"""Conserva los diez campos de Reto 1 y agrega PENDIENTE para fallback."""

from typing import Literal

from pydantic import Field

from Reto_1.app.models import EMPLEADO_EJEMPLO, Empleado as EmpleadoOriginal


class Empleado(EmpleadoOriginal):
    estado: Literal["ACTIVO", "PENDIENTE"] = Field(
        default="ACTIVO",
        description="Estado del empleado; PENDIENTE indica validacion aplazada del departamento",
        examples=["ACTIVO", "PENDIENTE"],
    )


__all__ = ["EMPLEADO_EJEMPLO", "Empleado"]
