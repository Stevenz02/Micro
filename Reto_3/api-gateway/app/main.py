import logging
from contextlib import asynccontextmanager
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from .config import Settings

logger = logging.getLogger(__name__)

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
}


def _filtered_headers(headers):
    return {key: value for key, value in headers.items() if key.lower() not in HOP_BY_HOP_HEADERS}


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
        title="Reto 3 - API Gateway",
        version="3.0.0",
        lifespan=lifespan,
        description="Punto unico de entrada para empleados y departamentos.",
    )

    async def proxy(request: Request, service_name: str, base_url: str):
        body = await request.body()
        url = _target_url(base_url, request.url.path, request.url.query)
        try:
            upstream = await request.app.state.http.request(
                request.method,
                url,
                content=body,
                headers=_filtered_headers(request.headers),
                timeout=request.app.state.settings.timeout,
            )
        except (httpx.TimeoutException, httpx.TransportError):
            logger.warning("Upstream no disponible: %s", service_name)
            return _upstream_error(service_name)
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=_filtered_headers(upstream.headers),
            media_type=upstream.headers.get("content-type"),
        )

    @app.get("/health", tags=["Salud"])
    async def health():
        return {"status": "ok", "service": "api-gateway"}

    @app.api_route("/empleados", methods=METHODS, tags=["Proxy"])
    @app.api_route("/empleados/{path:path}", methods=METHODS, tags=["Proxy"])
    async def empleados(request: Request):
        return await proxy(request, "empleados-service", request.app.state.settings.empleados_url)

    @app.api_route("/departamentos", methods=METHODS, tags=["Proxy"])
    @app.api_route("/departamentos/{path:path}", methods=METHODS, tags=["Proxy"])
    async def departamentos(request: Request):
        return await proxy(request, "departamentos-service", request.app.state.settings.departamentos_url)

    return app


app = create_app()
