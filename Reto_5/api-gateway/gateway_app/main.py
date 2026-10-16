import logging
import json
import copy
from contextlib import asynccontextmanager
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from shared.tokens import InvalidToken, validate_access

from .config import Settings

logger = logging.getLogger(__name__)


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(examples=["usuario@empresa.com"])
    password: str = Field(examples=["ClavePersonal2026"])


class RecoverInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(examples=["usuario@empresa.com"])


class ResetInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(description="Token recibido en la notificación de seguridad")
    newPassword: str = Field(description="Contraseña nueva según la política de Auth")


class ChangeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    currentPassword: str
    newPassword: str


class TokenOutput(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
    "x-authenticated-employee-id",
    "x-authenticated-role",
}

PUBLIC_ROUTES = {
    ("GET", "/health"),
    ("GET", "/docs"),
    ("GET", "/redoc"),
    ("GET", "/openapi.json"),
    ("GET", "/auth/docs"),
    ("GET", "/auth/openapi.json"),
    ("GET", "/perfiles/docs"),
    ("GET", "/perfiles/openapi.json"),
    ("GET", "/notificaciones/docs"),
    ("GET", "/notificaciones/openapi.json"),
    ("GET", "/notificaciones/openapi.json/swagger-config"),
    ("GET", "/vacaciones/docs"),
    ("GET", "/vacaciones/v1/openapi.json"),
    ("GET", "/departamentos/docs"),
    ("GET", "/departamentos/openapi.json"),
    ("GET", "/empleados/docs"),
    ("GET", "/empleados/openapi.json"),
    ("POST", "/auth/login"),
    ("POST", "/auth/recover-password"),
    ("POST", "/auth/reset-password"),
}


def _filtered_headers(headers, *, include_authorization=True):
    excluded = HOP_BY_HOP_HEADERS | (set() if include_authorization else {"authorization"})
    return {key: value for key, value in headers.items() if key.lower() not in excluded}


def _target_url(base_url: str, path: str, query: str) -> str:
    parsed = urlsplit(base_url)
    base_path = parsed.path.rstrip("/")
    target_path = f"{base_path}{path}"
    return urlunsplit((parsed.scheme, parsed.netloc, target_path, query, ""))


def _upstream_error(service: str):
    return JSONResponse(
        status_code=503,
        content={
            "error": "upstream_unavailable",
            "service": service,
            "message": "El servicio solicitado no esta disponible temporalmente",
        },
    )


OPENAPI_PATHS = {
    "/empleados/openapi.json", "/departamentos/openapi.json",
    "/perfiles/openapi.json", "/notificaciones/openapi.json",
    "/vacaciones/v1/openapi.json",
}


def _secure_openapi(body: bytes) -> bytes:
    schema = json.loads(body)
    if not isinstance(schema, dict):
        raise ValueError("El esquema OpenAPI debe ser un objeto")
    schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
        "type": "http", "scheme": "bearer", "bearerFormat": "JWT"
    }
    schema["servers"] = [{"url": "/"}]
    for path, operations in schema.get("paths", {}).items():
        if path.split("/")[1:2] and path.split("/")[1] in {
            "empleados", "departamentos", "perfiles", "notificaciones", "vacaciones"
        }:
            for method, operation in operations.items():
                if method.upper() in METHODS:
                    operation["security"] = [{"BearerAuth": []}]
    return json.dumps(schema, ensure_ascii=False).encode("utf-8")


def _merge_service_openapi(gateway_schema: dict, source: dict, service: str) -> None:
    """Copy the public service contract into the single Gateway document."""
    if not isinstance(source.get("paths"), dict):
        return
    prefix = "/" + service.lower()
    if any(path == prefix or path.startswith(prefix + "/")
           for path in source["paths"]):
        for path in list(gateway_schema["paths"]):
            if path == prefix or path.startswith(prefix + "/"):
                operations = gateway_schema["paths"][path]
                for method in list(operations):
                    if isinstance(operations[method], dict) and operations[method].get("tags") == ["Proxy"]:
                        del operations[method]
                if not operations:
                    del gateway_schema["paths"][path]
    schemas = source.get("components", {}).get("schemas", {})
    names = {name: f"{service}_{name}" for name in schemas}

    def namespace_refs(value):
        if isinstance(value, dict):
            return {key: (f"#/components/schemas/{names[ref]}"
                          if key == "$ref" and isinstance(item, str)
                          and item.startswith("#/components/schemas/")
                          and (ref := item.rsplit("/", 1)[-1]) in names
                          else namespace_refs(item)) for key, item in value.items()}
        if isinstance(value, list):
            return [namespace_refs(item) for item in value]
        return value

    target_schemas = gateway_schema.setdefault("components", {}).setdefault("schemas", {})
    for name, definition in schemas.items():
        target_schemas[names[name]] = namespace_refs(definition)
    for path, methods in source["paths"].items():
        # The upstream health endpoint is not reachable at this path through the Gateway.
        if path == "/health" or not isinstance(methods, dict):
            continue
        target = gateway_schema["paths"].setdefault(path, {})
        for method, operation in methods.items():
            if method.upper() not in METHODS or not isinstance(operation, dict):
                continue
            # Gateway declares the public Auth requests and the login token response
            # more precisely than Auth's generated schema (which has no response_model).
            if service == "Auth" and method in target:
                continue
            documented = namespace_refs(operation)
            documented["tags"] = [service]
            if path.startswith("/auth/") and path in {
                "/auth/login", "/auth/recover-password", "/auth/reset-password"
            }:
                documented.pop("security", None)
            else:
                documented["security"] = [{"BearerAuth": []}]
                documented.setdefault("responses", {}).setdefault(
                    "401", {"description": "Bearer ausente o inválido"})
                documented["responses"].setdefault(
                    "403", {"description": "Permiso insuficiente"})
            target[method] = documented


def create_app(settings: Settings | None = None, client: httpx.AsyncClient | None = None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.settings = settings or Settings.from_env()
        if client is not None:
            app.state.http = client
            yield
        else:
            async with httpx.AsyncClient(follow_redirects=False, trust_env=False) as http:
                app.state.http = http
                yield

    app = FastAPI(
        title="Reto 5 - API Gateway",
        version="5.0.0",
        lifespan=lifespan,
        openapi_url=None,
        description=("Entrada única con validación HS256, RBAC y propiedad del perfil. "
                     "Para explorar contratos completos use /auth/docs, /empleados/docs, "
                     "/departamentos/docs, /perfiles/docs, /notificaciones/docs y /vacaciones/docs. "
                     "Obtenga access_token en POST /auth/login y péguelo en Authorize."),
    )

    @app.middleware("http")
    async def authorize(request: Request, call_next):
        method, path = request.method, request.scope["path"]
        public_docs_asset = method == "GET" and (
            path.startswith("/notificaciones/swagger-ui/")
            or path.startswith("/vacaciones/docs/")
        )
        if (method, path) in PUBLIC_ROUTES or public_docs_asset:
            return await call_next(request)
        authorization = request.headers.get("authorization", "")
        scheme, separator, token = authorization.partition(" ")
        if scheme != "Bearer" or not separator or not token or any(char.isspace() for char in token):
            return JSONResponse(status_code=401, content={"detail": "Bearer access token requerido"})
        try:
            claims = validate_access(token, request.app.state.settings.jwt_secret)
        except InvalidToken:
            return JSONResponse(status_code=401, content={"detail": "Access token inválido"})
        role = claims["role"]
        if path.startswith("/auth/"):
            allowed = method == "POST" and path == "/auth/change-password"
        elif (path.startswith("/notificaciones/seguridad/")
              and path.endswith("/token")):
            allowed = role == "ADMIN" and method == "GET"
        elif method in {"GET", "HEAD"}:
            allowed = True
        elif role == "ADMIN":
            allowed = True
        else:
            segments = path.split("/")
            allowed = (method == "PUT" and len(segments) == 3
                       and segments[1] == "perfiles" and segments[2] == claims["sub"])
        if not allowed:
            return JSONResponse(status_code=403, content={"detail": "Permiso insuficiente"})
        request.state.claims = claims
        return await call_next(request)

    async def proxy(request: Request, service_name: str, base_url: str, target_path: str | None = None):
        body = await request.body()
        url = _target_url(base_url, target_path or request.url.path, request.url.query)
        is_auth = service_name == "auth-service"
        headers = _filtered_headers(request.headers, include_authorization=is_auth)
        claims = getattr(request.state, "claims", None)
        if claims is not None:
            headers["X-Authenticated-Employee-Id"] = claims["sub"]
            headers["X-Authenticated-Role"] = claims["role"]
        try:
            upstream = await request.app.state.http.request(
                request.method,
                url,
                content=body,
                headers=headers,
                timeout=request.app.state.settings.timeout,
            )
        except (httpx.TimeoutException, httpx.TransportError):
            logger.warning("Upstream no disponible: %s", service_name)
            return _upstream_error(service_name)
        response_body = upstream.content
        if request.url.path in OPENAPI_PATHS and upstream.status_code == 200:
            try:
                response_body = _secure_openapi(response_body)
            except (json.JSONDecodeError, TypeError, ValueError):
                logger.warning("OpenAPI inválido de %s", service_name)
                return _upstream_error(service_name)
        return Response(
            content=response_body,
            status_code=upstream.status_code,
            headers=_filtered_headers(upstream.headers),
            media_type=upstream.headers.get("content-type"),
        )

    @app.get("/health", tags=["Salud"])
    async def health():
        return {"status": "ok", "service": "api-gateway"}

    @app.get("/health/dependencies", tags=["Salud"])
    async def dependencies(request: Request):
        return await proxy(request, "empleados-service", request.app.state.settings.empleados_url)

    @app.get("/empleados/docs", include_in_schema=False)
    async def empleados_docs():
        return get_swagger_ui_html(openapi_url="/empleados/openapi.json", title="Empleados Swagger")

    @app.get("/empleados/openapi.json", include_in_schema=False)
    async def empleados_openapi(request: Request):
        return await proxy(request, "empleados-service", request.app.state.settings.empleados_url,
                           target_path="/openapi.json")

    @app.get("/departamentos/docs", include_in_schema=False)
    async def departamentos_docs():
        return get_swagger_ui_html(openapi_url="/departamentos/openapi.json", title="Departamentos Swagger")

    @app.get("/departamentos/openapi.json", include_in_schema=False)
    async def departamentos_openapi(request: Request):
        return await proxy(request, "departamentos-service", request.app.state.settings.departamentos_url,
                           target_path="/openapi.json")

    async def empleados(request: Request):
        return await proxy(request, "empleados-service", request.app.state.settings.empleados_url)

    async def departamentos(request: Request):
        return await proxy(request, "departamentos-service", request.app.state.settings.departamentos_url)

    async def perfiles(request: Request):
        return await proxy(request, "perfiles-service", request.app.state.settings.perfiles_url)

    async def notificaciones(request: Request):
        return await proxy(request, "notificaciones-service", request.app.state.settings.notificaciones_url)

    async def vacaciones(request: Request):
        return await proxy(request, "vacaciones-service", request.app.state.settings.vacaciones_url)

    for prefix, endpoint in (
        ("empleados", empleados),
        ("departamentos", departamentos),
        ("perfiles", perfiles),
        ("notificaciones", notificaciones),
        ("vacaciones", vacaciones),
    ):
        for route_path in (f"/{prefix}", f"/{prefix}/{{path:path}}"):
            for method in METHODS:
                app.add_api_route(route_path, endpoint, methods=[method], tags=["Proxy"])

    @app.post("/auth/login", tags=["Autenticación"], response_model=TokenOutput,
              responses={401: {"description": "Credenciales inválidas"},
                         422: {"description": "Cuerpo inválido"},
                         503: {"description": "Auth no disponible"}})
    async def auth_login(request: Request):
        return await proxy(request, "auth-service", request.app.state.settings.auth_url)

    @app.post("/auth/recover-password", tags=["Autenticación"], status_code=202,
              responses={422: {"description": "Cuerpo inválido"},
                         503: {"description": "Auth no disponible"}})
    async def auth_recover(request: Request):
        return await proxy(request, "auth-service", request.app.state.settings.auth_url)

    @app.post("/auth/reset-password", tags=["Autenticación"],
              responses={400: {"description": "Token o contraseña inválidos"},
                         422: {"description": "Cuerpo inválido"}})
    async def auth_reset(request: Request):
        return await proxy(request, "auth-service", request.app.state.settings.auth_url)

    @app.post("/auth/change-password", tags=["Autenticación"],
              responses={400: {"description": "Contraseña actual incorrecta o nueva inválida"},
                         401: {"description": "Token inválido o cuenta no disponible"},
                         409: {"description": "La cuenta cambió durante la operación"},
                         422: {"description": "Cuerpo inválido"}})
    async def auth_change(request: Request):
        return await proxy(request, "auth-service", request.app.state.settings.auth_url)

    @app.api_route("/auth", methods=METHODS, include_in_schema=False)
    @app.api_route("/auth/{path:path}", methods=METHODS, include_in_schema=False)
    async def auth(request: Request):
        return await proxy(request, "auth-service", request.app.state.settings.auth_url)

    def custom_openapi():
        if app.openapi_schema is None:
            schema = get_openapi(title=app.title, version=app.version, description=app.description,
                                 routes=app.routes)
            schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
                "type": "http", "scheme": "bearer", "bearerFormat": "JWT"
            }
            for path, model in {
                "/auth/login": LoginInput,
                "/auth/recover-password": RecoverInput,
                "/auth/reset-password": ResetInput,
                "/auth/change-password": ChangeInput,
            }.items():
                schema["paths"][path]["post"]["requestBody"] = {
                    "required": True,
                    "content": {"application/json": {"schema": model.model_json_schema()}},
                }
            for path, methods in schema["paths"].items():
                for method, operation in methods.items():
                    if method.upper() in METHODS and (method.upper(), path) not in PUBLIC_ROUTES:
                        operation["security"] = [{"BearerAuth": []}]
            app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi

    @app.get("/docs", include_in_schema=False)
    async def gateway_docs():
        return get_swagger_ui_html(openapi_url="/openapi.json", title="Reto 6 - Gateway Swagger")

    @app.get("/redoc", include_in_schema=False)
    async def gateway_redoc():
        return get_redoc_html(openapi_url="/openapi.json", title="Reto 6 - Gateway ReDoc")

    @app.get("/openapi.json", include_in_schema=False)
    async def gateway_openapi(request: Request):
        if not hasattr(app.state, "combined_openapi"):
            schema = copy.deepcopy(custom_openapi())
            sources = (
                ("Auth", request.app.state.settings.auth_url, "/auth/openapi.json"),
                ("Empleados", request.app.state.settings.empleados_url, "/openapi.json"),
                ("Departamentos", request.app.state.settings.departamentos_url, "/openapi.json"),
                ("Perfiles", request.app.state.settings.perfiles_url, "/perfiles/openapi.json"),
                ("Notificaciones", request.app.state.settings.notificaciones_url, "/notificaciones/openapi.json"),
                ("Vacaciones", request.app.state.settings.vacaciones_url, "/vacaciones/v1/openapi.json"),
            )
            merged = 0
            for name, base, path in sources:
                try:
                    response = await request.app.state.http.get(
                        _target_url(base, path, ""), timeout=request.app.state.settings.timeout)
                    response.raise_for_status()
                    source = response.json()
                    if not isinstance(source, dict) or not isinstance(source.get("paths"), dict) or not source["paths"]:
                        raise ValueError("OpenAPI sin rutas")
                    _merge_service_openapi(schema, source, name)
                    merged += 1
                except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
                    logger.warning("No se pudo incorporar OpenAPI de %s: %s", name, exc)
            schema["servers"] = [{"url": "/"}]
            if merged == len(sources):
                app.state.combined_openapi = schema
            return JSONResponse(schema)
        return JSONResponse(app.state.combined_openapi)

    return app


app = create_app()
