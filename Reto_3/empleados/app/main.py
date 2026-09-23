import asyncio
import logging
from contextlib import asynccontextmanager, suppress

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
    400: {"model": Error, "description": "Email, numero o id duplicado; departamento inexistente"},
    404: {"model": Error, "description": "Recurso no encontrado"},
    500: {"model": Error, "description": "Error interno de persistencia"},
    503: {"model": Error, "description": "Base de datos no disponible"},
}


def reconciliar_pendientes(repo, departamentos, limit=50):
    """Revisa empleados PENDIENTE y actualiza solo con evidencia del servicio de departamentos."""
    resultado = {"activados": 0, "rechazados": 0, "pendientes": 0}
    for empleado in repo.listar_pendientes(limit):
        try:
            departamentos.validar(empleado.departamentoId)
        except HTTPException as exc:
            if exc.status_code == 400:
                repo.actualizar_estado(empleado.id, "RECHAZADO")
                resultado["rechazados"] += 1
            else:
                resultado["pendientes"] += 1
        else:
            repo.actualizar_estado(empleado.id, "ACTIVO")
            resultado["activados"] += 1
    return resultado


async def reconciliar_periodicamente(app, intervalo):
    while True:
        await asyncio.sleep(intervalo)
        try:
            resultado = await asyncio.to_thread(
                reconciliar_pendientes,
                app.state.repository,
                app.state.departamentos,
            )
            if any(resultado.values()):
                logger.info("Reconciliacion de empleados pendientes: %s", resultado)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("No se pudo reconciliar empleados pendientes")


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
                tarea_reconciliacion = asyncio.create_task(
                    reconciliar_periodicamente(app, settings.reconciliation_interval)
                )
                try:
                    yield
                finally:
                    tarea_reconciliacion.cancel()
                    with suppress(asyncio.CancelledError):
                        await tarea_reconciliacion

    app = FastAPI(
        title="Reto 3 - Empleados",
        version="3.0.0",
        lifespan=lifespan,
        description="Persistencia independiente y validacion de departamentos por HTTP con Circuit Breaker.",
    )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        if exc.status_code == 405 or (exc.status_code == 404 and exc.detail == "Not Found"):
            return JSONResponse(status_code=404, content={"detail": "Recurso no encontrado"})
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(psycopg.Error)
    async def database_error(request, exc):
        logger.error("Error de base de datos: %s", type(exc).__name__)
        code = 503 if isinstance(exc, psycopg.OperationalError) else 500
        return JSONResponse(
            status_code=code,
            content={"detail": "No se pudo completar la operacion en la base de datos"},
        )

    @app.get("/health", tags=["Salud"], responses={503: ERRORS[503], 500: ERRORS[500]})
    def health():
        app.state.repository.ready()
        return {"status": "ok"}

    @app.get("/health/dependencies", tags=["Salud"], responses={503: ERRORS[503]})
    def dependencies():
        return {"status": "ok", "dependencies": [app.state.departamentos.estado()]}

    def crear_empleado(repo, empleado):
        try:
            return repo.crear(empleado)
        except psycopg.errors.UniqueViolation as exc:
            field = {
                "empleados_email_key": "email",
                "empleados_numero_empleado_key": "numero de empleado",
                "empleados_pkey": "id",
            }.get(exc.diag.constraint_name, "identificador unico")
            raise HTTPException(400, f"El {field} ya esta registrado") from exc

    @app.post(
        "/empleados",
        response_model=Empleado,
        status_code=201,
        tags=["Empleados"],
        responses={
            **ERRORS,
            202: {
                "model": Empleado,
                "description": "Empleado recibido en estado PENDIENTE por dependencia no disponible",
            },
        },
        summary="Registrar empleado activo o pendiente",
    )
    def registrar(empleado: Empleado):
        repo = app.state.repository
        if repo.existe_email(empleado.email):
            raise HTTPException(400, f"El email {empleado.email} ya esta registrado")
        if repo.existe_numero(empleado.numeroEmpleado):
            raise HTTPException(400, f"El numero de empleado {empleado.numeroEmpleado} ya esta registrado")
        try:
            app.state.departamentos.validar(empleado.departamentoId)
        except HTTPException as exc:
            if exc.status_code != 503:
                raise
            pendiente = empleado.model_copy(update={"estado": "PENDIENTE"})
            creado = crear_empleado(repo, pendiente)
            return JSONResponse(status_code=202, content=creado.model_dump(mode="json"))
        return crear_empleado(repo, empleado.model_copy(update={"estado": "ACTIVO"}))

    @app.get(
        "/empleados",
        response_model=list[Empleado],
        tags=["Empleados"],
        responses={500: ERRORS[500], 503: ERRORS[503]},
        summary="Listar empleados",
    )
    def listar():
        return app.state.repository.listar()

    @app.get(
        "/empleados/{id}",
        response_model=Empleado,
        tags=["Empleados"],
        responses={404: ERRORS[404], 500: ERRORS[500], 503: ERRORS[503]},
        summary="Consultar empleado",
    )
    def obtener(id: str):
        empleado = app.state.repository.obtener(id)
        if empleado is None:
            raise HTTPException(404, f"El empleado con id {id} no existe")
        return empleado

    return app


app = create_app()
