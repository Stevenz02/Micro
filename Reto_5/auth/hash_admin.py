"""Genera un hash bcrypt para ADMIN_PASSWORD_HASH sin registrar la contraseña."""

from getpass import getpass

from auth_app.passwords import hash_password


if __name__ == "__main__":
    print(hash_password(getpass("Contraseña del administrador: ")))
