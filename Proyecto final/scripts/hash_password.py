"""Imprime un hash bcrypt del secreto recibido por entorno, nunca el secreto original."""

import os

import bcrypt


password = os.environ["ADMIN_PASSWORD"].encode("utf-8")
print(bcrypt.hashpw(password, bcrypt.gensalt(rounds=12)).decode("ascii"))
