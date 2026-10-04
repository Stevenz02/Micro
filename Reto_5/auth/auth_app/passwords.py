"""Política y hash de credenciales; bcrypt rechaza entradas que truncaría a 72 bytes."""

import bcrypt


def validate_new_password(password: str) -> None:
    if not 12 <= len(password) <= 128 or len(password.encode("utf-8")) > 72:
        raise ValueError("La contraseña debe tener 12 a 128 caracteres y máximo 72 bytes UTF-8")
    if not any(c.islower() for c in password) or not any(c.isupper() for c in password):
        raise ValueError("La contraseña requiere mayúscula y minúscula")
    if not any(c.isdigit() for c in password):
        raise ValueError("La contraseña requiere un número")


def hash_password(password: str) -> str:
    validate_new_password(password)
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def check_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("ascii"))
    except (ValueError, UnicodeError):
        return False
