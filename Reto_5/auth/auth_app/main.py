"""API de identidad. La conexión RabbitMQ espera los payloads oficiales ausentes."""

import logging
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict

from shared.tokens import InvalidToken, issue_access, issue_reset, validate_access, validate_reset

from .config import Settings, database_config
from .events import EventConsumer, EventProcessor, RabbitPublisher, reset_expiration
from .passwords import check_password, hash_password
from .repository import ACTIVE, RETIRED, Repository

logger = logging.getLogger(__name__)
bearer = HTTPBearer(auto_error=False, scheme_name="BearerAuth")


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str
    password: str


class RecoverRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str


class ResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str
    newPassword: str


class ChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    currentPassword: str
    newPassword: str


def create_app(repository=None, settings=None, recovery_sender: Callable | None = None,
               activation_sender: Callable | None = None, publisher=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.settings = settings or Settings.from_env()
        app.state.repository = repository or Repository(database_config())
        if repository is None:
            app.state.repository.ensure_schema()
            s = app.state.settings
            if s.admin_employee_id:
                app.state.repository.seed_admin(s.admin_employee_id, s.admin_email, s.admin_password_hash)
        app.state.publisher = publisher or (RabbitPublisher() if repository is None else None)
        app.state.consumer = None
        if app.state.publisher is not None:
            app.state.event_processor = EventProcessor(app.state.repository, app.state.publisher,
                                                        app.state.settings.jwt_secret,
                                                        app.state.settings.reset_ttl_seconds)
            if repository is None:
                app.state.consumer = EventConsumer(app.state.event_processor)
                app.state.consumer.start()
        try:
            yield
        finally:
            if app.state.consumer is not None:
                app.state.consumer.stop()

    app = FastAPI(title="Reto 5 - Auth Service", version="5.0.0", lifespan=lifespan,
                  docs_url="/auth/docs", openapi_url="/auth/openapi.json", redoc_url=None,
                  description="Identidad local con JWT HS256 y cuentas por empleado.")

    def current_account(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if credentials is None or credentials.scheme != "Bearer":
            raise HTTPException(401, "Bearer access token requerido")
        try:
            claims = validate_access(credentials.credentials, app.state.settings.jwt_secret)
        except InvalidToken as exc:
            raise HTTPException(401, "Access token inválido") from exc
        account = app.state.repository.get_by_id(claims["sub"])
        if account is None or account.status != ACTIVE or account.role != claims["role"]:
            raise HTTPException(401, "Cuenta no disponible")
        return account

    @app.get("/health", tags=["Salud"])
    def health():
        app.state.repository.ensure_schema()
        return {"status": "ok"}

    @app.post("/auth/login", tags=["Autenticación"])
    def login(data: LoginRequest):
        account = app.state.repository.get_by_email(data.email)
        if account is None or account.status != ACTIVE or not check_password(data.password, account.password_hash):
            raise HTTPException(401, "Credenciales inválidas")
        token = issue_access(app.state.settings.jwt_secret, account.employee_id, account.role,
                             app.state.settings.access_ttl_seconds)
        return {"access_token": token, "token_type": "bearer",
                "expires_in": app.state.settings.access_ttl_seconds}

    @app.post("/auth/recover-password", status_code=202, tags=["Autenticación"])
    def recover_password(data: RecoverRequest):
        if recovery_sender is None and app.state.publisher is None:
            raise HTTPException(503, "Recuperación temporalmente no disponible")
        account = app.state.repository.get_by_email(data.email)
        if account is not None and account.status != RETIRED:
            token = issue_reset(app.state.settings.jwt_secret, account.employee_id,
                                account.credential_version, app.state.settings.reset_ttl_seconds)
            try:
                if recovery_sender is not None:
                    recovery_sender(account, token)
                else:
                    app.state.publisher.publish("usuario.recuperacion", {
                        "email": account.email, "tokenRecuperacion": token,
                        "expiraEn": reset_expiration(token, app.state.settings.jwt_secret),
                    })
            except Exception:
                logger.exception("No se pudo iniciar una recuperación de contraseña")
        return {"detail": "Si la cuenta existe, recibirá instrucciones de recuperación"}

    @app.post("/auth/reset-password", tags=["Autenticación"])
    def reset_password(data: ResetRequest):
        try:
            claims = validate_reset(data.token, app.state.settings.jwt_secret)
        except InvalidToken as exc:
            raise HTTPException(400, "Token de recuperación inválido") from exc
        account = app.state.repository.get_by_id(claims["sub"])
        if account is None or account.status == RETIRED or account.credential_version != claims["credentialVersion"]:
            raise HTTPException(400, "Token de recuperación inválido")
        try:
            new_hash = hash_password(data.newPassword)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        updated = app.state.repository.set_password(account.employee_id, account.credential_version, new_hash)
        if updated is None:
            raise HTTPException(400, "Token de recuperación inválido")
        if account.status != ACTIVE and updated.status == ACTIVE:
            try:
                if activation_sender is not None:
                    activation_sender(updated)
                elif app.state.publisher is not None:
                    app.state.publisher.publish("cuenta.activada", {
                        "empleadoId": updated.employee_id, "email": updated.email,
                        "motivo": "ACTIVACION_INICIAL",
                    })
            except Exception:
                logger.exception("No se pudo notificar la activación de la cuenta")
        return {"detail": "Contraseña establecida"}

    @app.post("/auth/change-password", tags=["Autenticación"])
    def change_password(data: ChangeRequest, account=Depends(current_account)):
        if not check_password(data.currentPassword, account.password_hash):
            raise HTTPException(400, "Contraseña actual incorrecta")
        try:
            new_hash = hash_password(data.newPassword)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        updated = app.state.repository.set_password(account.employee_id, account.credential_version, new_hash)
        if updated is None:
            raise HTTPException(409, "La cuenta cambió; vuelva a intentarlo")
        return {"detail": "Contraseña actualizada"}

    return app


app = create_app()
