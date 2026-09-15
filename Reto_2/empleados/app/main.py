import logging
from contextlib import asynccontextmanager

import httpx
import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import Settings, database_config
from .departamentos import DepartamentosClient
from .models import Empleado
from .repository import Repository

logger = logging.getLogger(__name__)


class Error(BaseModel):
    detail: str


ERRORS = {
    400: {"model": Error, "description": "Email, número o id duplicado; departamento inexistente"},
    404: {"model": Error, "description": "Recurso no encontrado"},
    500: {"model": Error, "description": "Error interno de persistencia"},
    503: {"model": Error, "description": "Dependencia no disponible; no se registra el empleado"},
}


def create_app(repository=None, departamentos=None):
    @asynccontextmanager
    async def lifespan(app):
        if repository is not None and departamentos is not None:
            app.state.repository = repository
            app.state.departamentos = departamentos
            yield
        else:
            settings = Settings.from_env()
            app.state.repository = Repository(database_config())
            with httpx.Client(follow_redirects=False, trust_env=False) as client:
                app.state.departamentos = DepartamentosClient(settings, client)
                yield

    app = FastAPI(title="Reto 2 - Empleados", version="2.0.0", lifespan=lifespan,
                  description="Persistencia independiente y validación de departamentos por HTTP.")

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        if exc.status_code == 405 or (exc.status_code == 404 and exc.detail == "Not Found"):
            return JSONResponse(status_code=404, content={"detail": "Recurso no encontrado"})
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(psycopg.Error)
    async def database_error(request, exc):
        logger.error("Error de base de datos: %s", type(exc).__name__)
        code = 503 if isinstance(exc, psycopg.OperationalError) else 500
        return JSONResponse(status_code=code, content={"detail": "No se pudo completar la operación en la base de datos"})

    @app.get("/health", tags=["Salud"], responses={503: ERRORS[503], 500: ERRORS[500]})
    def health():
        app.state.repository.ready()
        return {"status": "ok"}

    @app.post("/empleados", response_model=Empleado, status_code=201,
              tags=["Empleados"], responses=ERRORS, summary="Registrar empleado activo")
    def registrar(empleado: Empleado):
        repo = app.state.repository
        if repo.existe_email(empleado.email):
            raise HTTPException(400, f"El email {empleado.email} ya está registrado")
        if repo.existe_numero(empleado.numeroEmpleado):
            raise HTTPException(400, f"El número de empleado {empleado.numeroEmpleado} ya está registrado")
        app.state.departamentos.validar(empleado.departamentoId)
        try:
            return repo.crear(empleado)
        except psycopg.errors.UniqueViolation as exc:
            field = {"empleados_email_key": "email", "empleados_numero_empleado_key": "número de empleado",
                     "empleados_pkey": "id"}.get(exc.diag.constraint_name, "identificador único")
            raise HTTPException(400, f"El {field} ya está registrado") from exc

    @app.get("/empleados", response_model=list[Empleado], tags=["Empleados"],
             responses={500: ERRORS[500], 503: ERRORS[503]}, summary="Listar empleados")
    def listar():
        return app.state.repository.listar()

    @app.get("/empleados/{id}", response_model=Empleado, tags=["Empleados"],
             responses={404: ERRORS[404], 500: ERRORS[500], 503: ERRORS[503]}, summary="Consultar empleado")
    def obtener(id: str):
        empleado = app.state.repository.obtener(id)
        if empleado is None:
            raise HTTPException(404, f"El empleado con id {id} no existe")
        return empleado

    return app


app = create_app()
