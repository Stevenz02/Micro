from app.models import Empleado


empleados: dict[str, Empleado] = {}


def limpiar() -> None:
    """Vacía el almacenamiento; se usa para aislar las pruebas."""
    empleados.clear()


def crear(empleado: Empleado) -> Empleado:
    empleados[empleado.id] = empleado
    return empleado


def obtener(empleado_id: str) -> Empleado | None:
    return empleados.get(empleado_id)


def existe_email(email: str) -> bool:
    return any(registrado.email == email for registrado in empleados.values())


def existe_numero(numero_empleado: str) -> bool:
    return any(
        registrado.numeroEmpleado == numero_empleado
        for registrado in empleados.values()
    )
