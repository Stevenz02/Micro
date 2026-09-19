"""Conserva los diez campos y validaciones de Reto 1; asigna ACTIVO al omitirlo."""

from typing import Literal

from pydantic import Field

from Reto_1.app.models import EMPLEADO_EJEMPLO, Empleado as EmpleadoOriginal


class Empleado(EmpleadoOriginal):
    estado: Literal["ACTIVO"] = Field(
        default="ACTIVO",
        description="Estado del empleado; se asigna ACTIVO si no se envía",
        examples=["ACTIVO"],
    )

__all__ = ["EMPLEADO_EJEMPLO", "Empleado"]
