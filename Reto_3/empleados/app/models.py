"""Conserva los diez campos de Reto 1 y agrega estados de conciliacion."""

from typing import Literal

from pydantic import Field

from Reto_1.app.models import EMPLEADO_EJEMPLO, Empleado as EmpleadoOriginal


class Empleado(EmpleadoOriginal):
    estado: Literal["ACTIVO", "PENDIENTE", "RECHAZADO"] = Field(
        default="ACTIVO",
        description="Estado del empleado; PENDIENTE indica validacion aplazada del departamento",
        examples=["ACTIVO", "PENDIENTE", "RECHAZADO"],
    )


__all__ = ["EMPLEADO_EJEMPLO", "Empleado"]
