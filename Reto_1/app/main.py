from typing import Annotated

from fastapi import FastAPI, HTTPException, Path, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import repository
from app.models import EMPLEADO_EJEMPLO, Empleado


TAGS_METADATA = [
    {
        "name": "Empleados",
        "description": "Operaciones para registrar y consultar empleados.",
    }
]

app = FastAPI(
    title="Reto 1 - Gestión de Empleados",
    description=(
        "API REST para el registro y consulta básica de empleados. "
        "Los datos se almacenan temporalmente en memoria."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=TAGS_METADATA,
)


@app.exception_handler(StarletteHTTPException)
async def manejar_error_http(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Uniforma rutas y métodos no soportados según el contrato del reto."""
    del request
    if exc.status_code == 405:
        return JSONResponse(status_code=404, content={"detail": "Recurso no encontrado"})
    if exc.status_code == 404 and exc.detail == "Not Found":
        return JSONResponse(status_code=404, content={"detail": "Recurso no encontrado"})
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.post(
    "/empleados",
    response_model=Empleado,
    status_code=200,
    tags=["Empleados"],
    summary="Registrar empleado",
    description=(
        "Registra un nuevo empleado en memoria. El email, el número de empleado "
        "y el ID deben ser únicos."
    ),
    response_description="Empleado registrado correctamente",
    responses={
        200: {
            "description": "Empleado registrado correctamente",
            "content": {"application/json": {"example": EMPLEADO_EJEMPLO}},
        },
        400: {
            "description": "Datos duplicados o inválidos",
            "content": {
                "application/json": {
                    "example": {
                        "detail": (
                            "El email juan.perez@empresa.com ya está registrado"
                        )
                    }
                }
            },
        },
        422: {"description": "Error de validación del cuerpo de la solicitud"},
    },
)
def registrar_empleado(empleado: Empleado) -> Empleado:
    if repository.obtener(empleado.id) is not None:
        raise HTTPException(
            status_code=400,
            detail=f"El empleado con id {empleado.id} ya está registrado",
        )
    if repository.existe_email(empleado.email):
        raise HTTPException(
            status_code=400,
            detail=f"El email {empleado.email} ya está registrado",
        )
    if repository.existe_numero(empleado.numeroEmpleado):
        raise HTTPException(
            status_code=400,
            detail=(
                f"El número de empleado {empleado.numeroEmpleado} ya está registrado"
            ),
        )
    return repository.crear(empleado)


@app.get(
    "/empleados/{id}",
    response_model=Empleado,
    tags=["Empleados"],
    summary="Consultar empleado por ID",
    description=(
        "Obtiene la información completa de un empleado utilizando su identificador."
    ),
    response_description="Empleado encontrado",
    responses={
        200: {
            "description": "Empleado encontrado",
            "content": {"application/json": {"example": EMPLEADO_EJEMPLO}},
        },
        404: {
            "description": "Empleado no encontrado",
            "content": {
                "application/json": {
                    "example": {"detail": "El empleado con id E999 no existe"}
                }
            },
        },
    },
)
def consultar_empleado(
    id: Annotated[
        str,
        Path(
            description="Identificador único del empleado",
            examples=["E001"],
        ),
    ],
) -> Empleado:
    empleado = repository.obtener(id)
    if empleado is None:
        raise HTTPException(
            status_code=404,
            detail=f"El empleado con id {id} no existe",
        )
    return empleado
