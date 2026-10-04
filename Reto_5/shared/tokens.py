"""Emisión y validación estricta de los dos tipos de JWT del Reto 5."""

from datetime import datetime, timedelta, timezone

import jwt


ISSUER = "rrhh-auth-service"
ACCESS = "ACCESS"
RESET_PASSWORD = "RESET_PASSWORD"


class InvalidToken(ValueError):
    pass


def _issue(secret: str, subject: str, token_type: str, lifetime: int, **claims) -> str:
    if not subject or lifetime <= 0:
        raise ValueError("Sujeto y duración del token deben ser válidos")
    now = datetime.now(timezone.utc)
    payload = {
        "iss": ISSUER,
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(seconds=lifetime),
        **claims,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def issue_access(secret: str, employee_id: str, role: str, lifetime: int) -> str:
    if role not in {"ADMIN", "USER"}:
        raise ValueError("Rol inválido")
    return _issue(secret, employee_id, ACCESS, lifetime, role=role)


def issue_reset(secret: str, employee_id: str, credential_version: int, lifetime: int) -> str:
    if credential_version < 0:
        raise ValueError("Versión de credencial inválida")
    return _issue(secret, employee_id, RESET_PASSWORD, lifetime, credentialVersion=credential_version)


def _decode(token: str, secret: str, expected_type: str) -> dict:
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            issuer=ISSUER,
            options={"require": ["iss", "sub", "type", "iat", "exp"], "verify_iat": True},
        )
    except jwt.PyJWTError as exc:
        raise InvalidToken("Token inválido") from exc
    if not isinstance(claims.get("sub"), str) or not claims["sub"].strip():
        raise InvalidToken("Sujeto inválido")
    if claims.get("type") != expected_type:
        raise InvalidToken("Tipo de token inválido")
    if not isinstance(claims.get("iat"), int) or not isinstance(claims.get("exp"), int):
        raise InvalidToken("Fechas inválidas")
    if claims["exp"] <= claims["iat"]:
        raise InvalidToken("Vigencia inválida")
    return claims


def validate_access(token: str, secret: str) -> dict:
    claims = _decode(token, secret, ACCESS)
    if claims.get("role") not in {"ADMIN", "USER"}:
        raise InvalidToken("Rol inválido")
    return claims


def validate_reset(token: str, secret: str) -> dict:
    claims = _decode(token, secret, RESET_PASSWORD)
    version = claims.get("credentialVersion")
    if not isinstance(version, int) or isinstance(version, bool) or version < 0:
        raise InvalidToken("Versión de credencial inválida")
    return claims
