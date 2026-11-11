"""Estado aislado por escenario y operaciones de preparación del dominio."""

import os
from datetime import datetime, timedelta, timezone

from .http_client import GatewayClient
from .polling import wait_until
from .test_data import employee, password, unique_suffix


class ScenarioState:
    def __init__(self):
        self.base_url = os.getenv("BASE_URL", "http://localhost:8080")
        self.poll_timeout = float(os.getenv("POLL_TIMEOUT_SECONDS", "30"))
        self.poll_interval = int(os.getenv("POLL_INTERVAL_MS", "500")) / 1000
        self.poll_max_attempts = int(os.getenv("POLL_MAX_ATTEMPTS", "120"))
        self.gateway = GatewayClient(self.base_url, float(os.getenv("HTTP_TIMEOUT_SECONDS", "10")))
        self.suffix = unique_suffix()
        self.current_token = None
        self.current_role = None
        self.admin_token = None
        self.user_token = None
        self.response = None
        self.employee = None
        self.department_id = None
        self.password = password()
        self.vacation_id = None
        self.activation_token = None

    def close(self):
        self.gateway.close()

    def send(self, method, path, *, token=None, body=None, headers=None):
        self.response = self.gateway.request(method, path, token=token, json=body, headers=headers)
        return self.response

    def expect(self, response, expected, action):
        assert response.status_code == expected, (
            f"{action}: esperaba HTTP {expected}, obtuvo {response.status_code}: {response.text[:500]}"
        )
        return response

    def wait(self, predicate, description, *, timeout=None):
        return wait_until(
            predicate, description,
            timeout=timeout or self.poll_timeout,
            interval=self.poll_interval,
            max_attempts=self.poll_max_attempts,
        )

    def login(self, email, secret):
        return self.gateway.request("POST", "/auth/login", json={"email": email, "password": secret})

    def admin(self):
        if self.admin_token:
            return self.admin_token
        email, secret = os.getenv("ADMIN_EMAIL"), os.getenv("ADMIN_PASSWORD")
        assert email and secret, "Configure ADMIN_EMAIL y ADMIN_PASSWORD para la suite BDD"
        response = self.expect(self.login(email, secret), 200, "Login ADMIN")
        self.admin_token = response.json()["access_token"]
        return self.admin_token

    def create_department(self):
        if self.department_id:
            return self.department_id
        self.department_id = f"D-{self.suffix}"
        self.expect(self.gateway.request("POST", "/departamentos", token=self.admin(), json={
            "id": self.department_id, "nombre": "Calidad E2E", "descripcion": "Pruebas automatizadas",
        }), 201, "Crear departamento")
        return self.department_id

    def create_employee(self):
        if self.employee:
            return self.employee
        self.employee = employee(self.suffix, self.create_department())
        response = self.gateway.request("POST", "/empleados", token=self.admin(), json=self.employee)
        self.response = response
        self.expect(response, 201, "Crear empleado")
        return self.employee

    def notifications(self):
        assert self.employee is not None
        response = self.gateway.request("GET", f"/notificaciones/{self.employee['id']}", token=self.admin())
        self.expect(response, 200, "Consultar notificaciones")
        return response.json()

    def notification(self, kind, phrase):
        return next((item for item in self.notifications()
                     if item["tipo"] == kind and phrase in item["mensaje"]), None)

    def wait_notification(self, kind, phrase):
        return self.wait(lambda: self.notification(kind, phrase), f"notificación {kind}: {phrase}")

    def get_activation_token(self):
        note = self.wait_notification("SEGURIDAD", "Cuenta creada")
        response = self.gateway.request(
            "GET", f"/notificaciones/seguridad/{note['id']}/token", token=self.admin(),
        )
        self.expect(response, 200, "Consultar token de activación simulado")
        self.activation_token = response.json()["token"]
        return self.activation_token

    def activate_employee(self):
        self.create_employee()
        token = self.get_activation_token()
        self.expect(self.gateway.request("POST", "/auth/reset-password", json={
            "token": token, "newPassword": self.password,
        }), 200, "Activar cuenta")
        response = self.wait(
            lambda: self._successful_user_login(),
            "cuenta activa y login USER",
        )
        self.user_token = response.json()["access_token"]
        return self.user_token

    def _successful_user_login(self):
        response = self.login(self.employee["email"], self.password)
        return response if response.status_code == 200 else None

    def utc_today(self):
        return datetime.now(timezone.utc).date().isoformat()

    def future_dates(self, offset=10, length=3):
        today = datetime.now(timezone.utc).date()
        return (today + timedelta(days=offset)).isoformat(), (today + timedelta(days=offset + length)).isoformat()

    def schedule(self, start, end):
        return self.send("POST", "/vacaciones", token=self.admin(), body={
            "empleadoId": self.employee["id"], "fechaInicio": start, "fechaFin": end,
        })
