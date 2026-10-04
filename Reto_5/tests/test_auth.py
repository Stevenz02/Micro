import sys
import json
import uuid
from dataclasses import replace
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "auth"))

from auth_app.config import Settings  # noqa: E402
from auth_app.lifecycle import AccountLifecycle  # noqa: E402
from auth_app.main import create_app  # noqa: E402
from auth_app.passwords import check_password, hash_password  # noqa: E402
from auth_app.repository import Account, ACTIVE, INACTIVE, RETIRED, SUSPENDED, next_status  # noqa: E402
from auth_app.events import EventProcessor, build_envelope  # noqa: E402
from shared.tokens import issue_access, issue_reset, validate_access, validate_reset, InvalidToken  # noqa: E402

SECRET = "test-only-secret-with-at-least-32-bytes"
OLD = "ContraseñaSegura123"
NEW = "NuevaContraseña456"


class FakeRepository:
    def __init__(self):
        self.accounts = {}
        self.processed = set()

    def ensure_schema(self):
        pass

    def add(self, id, email, status=ACTIVE, password=OLD):
        account = Account(id, email, "USER", status, hash_password(password) if password else None, 0)
        self.accounts[id] = account
        return account

    def get_by_email(self, email):
        return next((a for a in self.accounts.values() if a.email == email.lower()), None)

    def get_by_id(self, employee_id):
        return self.accounts.get(employee_id)

    def set_password(self, employee_id, expected_version, password_hash):
        account = self.accounts.get(employee_id)
        if account is None or account.status == RETIRED or account.credential_version != expected_version:
            return None
        updated = replace(account, password_hash=password_hash, credential_version=expected_version + 1,
                          status=ACTIVE if account.status == INACTIVE else account.status)
        self.accounts[employee_id] = updated
        return updated

    def create_employee(self, employee_id, email):
        if employee_id in self.accounts:
            return None
        account = Account(employee_id, email.lower(), "USER", INACTIVE, None, 0)
        self.accounts[employee_id] = account
        return account

    def transition(self, employee_id, from_status, to_status):
        account = self.accounts.get(employee_id)
        if account is None or account.status not in from_status:
            return None
        updated = replace(account, status=to_status)
        self.accounts[employee_id] = updated
        return updated

    def apply_event(self, event):
        if event.id in self.processed:
            return False, None
        account = self.get_by_id(event.data["empleadoId"])
        if event.type == "empleado.creado":
            updated = self.create_employee(event.data["empleadoId"], event.data["email"])
        else:
            if account is None:
                raise RuntimeError("Cuenta ausente")
            status = next_status(account.status, account.password_hash, event.type)
            updated = replace(account, status=status) if status else account
            self.accounts[account.employee_id] = updated
        self.processed.add(event.id)
        return updated is not None and updated != account, updated


def app_for(repo, sender=None, activation=None, publisher=None):
    return TestClient(create_app(repo, Settings(SECRET), sender, activation, publisher))


def test_login_hash_and_account_states():
    repo = FakeRepository()
    active = repo.add("E001", "e001@example.test")
    repo.add("E002", "e002@example.test", INACTIVE, None)
    repo.add("E003", "e003@example.test", SUSPENDED)
    repo.add("E004", "e004@example.test", RETIRED)
    assert active.password_hash != OLD and check_password(OLD, active.password_hash)
    with app_for(repo) as client:
        response = client.post("/auth/login", json={"email": "e001@example.test", "password": OLD})
        assert response.status_code == 200
        claims = validate_access(response.json()["access_token"], SECRET)
        assert claims["sub"] == "E001" and claims["role"] == "USER"
        assert "password" not in claims
        for email, password in (("e001@example.test", "incorrect"), ("e002@example.test", OLD),
                                ("e003@example.test", OLD), ("e004@example.test", OLD)):
            assert client.post("/auth/login", json={"email": email, "password": password}).status_code == 401


def test_reset_token_validation_and_one_time_credential_version():
    repo = FakeRepository()
    repo.add("E001", "e001@example.test", INACTIVE, None)
    token = issue_reset(SECRET, "E001", 0, 1800)
    expired = jwt.encode({"iss": "rrhh-auth-service", "sub": "E001", "type": "RESET_PASSWORD",
                          "iat": 1, "exp": 2, "credentialVersion": 0}, SECRET, algorithm="HS256")
    invalid = [expired, token + "altered", issue_access(SECRET, "E001", "USER", 900), "malformed"]
    with app_for(repo) as client:
        for candidate in invalid:
            assert client.post("/auth/reset-password", json={"token": candidate, "newPassword": NEW}).status_code == 400
        assert client.post("/auth/reset-password", json={"token": token, "newPassword": NEW}).status_code == 200
        assert repo.get_by_id("E001").status == ACTIVE
        assert client.post("/auth/reset-password", json={"token": token, "newPassword": OLD}).status_code == 400
        assert client.post("/auth/login", json={"email": "e001@example.test", "password": NEW}).status_code == 200


def test_change_password_is_bound_to_token_subject():
    repo = FakeRepository()
    repo.add("E001", "e001@example.test")
    repo.add("E002", "e002@example.test")
    access = issue_access(SECRET, "E001", "USER", 900)
    headers = {"Authorization": f"Bearer {access}"}
    with app_for(repo) as client:
        assert client.post("/auth/change-password", json={"currentPassword": OLD, "newPassword": NEW}).status_code == 401
        assert client.post("/auth/change-password", headers=headers,
                           json={"currentPassword": "wrong", "newPassword": NEW}).status_code == 400
        assert client.post("/auth/change-password", headers=headers,
                           json={"currentPassword": OLD, "newPassword": NEW, "empleadoId": "E002"}).status_code == 422
        assert client.post("/auth/change-password", headers=headers,
                           json={"currentPassword": OLD, "newPassword": NEW}).status_code == 200
        assert client.post("/auth/login", json={"email": "e001@example.test", "password": OLD}).status_code == 401
        assert client.post("/auth/login", json={"email": "e001@example.test", "password": NEW}).status_code == 200
        assert client.post("/auth/login", json={"email": "e002@example.test", "password": OLD}).status_code == 200


def test_recovery_response_does_not_disclose_email_and_uses_reset_token():
    repo = FakeRepository()
    repo.add("E001", "e001@example.test")
    sent = []
    with app_for(repo, lambda account, token: sent.append((account, token))) as client:
        existing = client.post("/auth/recover-password", json={"email": "e001@example.test"})
        missing = client.post("/auth/recover-password", json={"email": "missing@example.test"})
    assert existing.status_code == missing.status_code == 202
    assert existing.json() == missing.json()
    assert len(sent) == 1
    assert validate_reset(sent[0][1], SECRET)["sub"] == "E001"


def test_retirement_during_vacation_is_permanent_and_transitions_are_idempotent():
    repo = FakeRepository()
    lifecycle = AccountLifecycle(repo, SECRET, 1800)
    created = lifecycle.employee_created("E001", "e001@example.test")
    assert created.changed and created.account.status == INACTIVE
    assert created.account.password_hash is None
    assert validate_reset(created.reset_token, SECRET)["sub"] == "E001"
    assert not lifecycle.employee_created("E001", "e001@example.test").changed
    repo.set_password("E001", 0, hash_password(OLD))
    assert lifecycle.vacation_started("E001").account.status == SUSPENDED
    assert not lifecycle.vacation_started("E001").changed
    assert lifecycle.employee_retired("E001").account.status == RETIRED
    assert not lifecycle.employee_retired("E001").changed
    assert not lifecycle.vacation_finished("E001").changed
    assert repo.get_by_id("E001").status == RETIRED
    lifecycle.employee_created("E002", "e002@example.test")
    repo.set_password("E002", 0, hash_password(OLD))
    assert lifecycle.vacation_started("E002").account.status == SUSPENDED
    assert lifecycle.vacation_finished("E002").account.status == ACTIVE
    assert not lifecycle.vacation_finished("E002").changed
    with app_for(repo) as client:
        assert client.post("/auth/login", json={"email": "e001@example.test", "password": OLD}).status_code == 401
        assert client.post("/auth/login", json={"email": "e002@example.test", "password": OLD}).status_code == 200


def test_invalid_access_claims_rejected():
    for token in (
        jwt.encode({"iss": "rrhh-auth-service", "sub": "E001", "type": "ACCESS", "role": "GUEST",
                    "iat": 1, "exp": 9999999999}, SECRET, algorithm="HS256"),
        jwt.encode({"iss": "rrhh-auth-service", "sub": "E001", "type": "ACCESS", "role": "USER",
                    "iat": 1, "exp": 9999999999}, SECRET, algorithm="HS384"),
    ):
        with pytest.raises(InvalidToken):
            validate_access(token, SECRET)


class FakePublisher:
    def __init__(self):
        self.messages = []

    def publish(self, event_type, data):
        self.messages.append((event_type, data))


def catalog_event(event_type, data, event_id=None):
    producer = "empleados-service" if event_type.startswith("empleado.") else "vacaciones-service"
    return json.dumps({
        "id": str(event_id or uuid.uuid4()), "type": event_type, "version": 1,
        "occurredAt": "2026-10-04T12:00:00Z", "producer": producer, "data": data,
    }).encode()


def created_data():
    return {"empleadoId": "E001", "nombre": "Ana", "apellido": "Demo", "email": "ana@example.test",
            "numeroEmpleado": "EMP001", "cargo": "Analista", "area": "TI", "departamentoId": "IT",
            "fechaIngreso": "2026-10-04", "estado": "ACTIVO"}


def test_catalog_onboarding_activation_and_recovery_payloads():
    repo, publisher = FakeRepository(), FakePublisher()
    processor = EventProcessor(repo, publisher, SECRET, 1800)
    body = catalog_event("empleado.creado", created_data())
    assert processor.process(body)
    assert not processor.process(body)
    assert len(publisher.messages) == 1
    event_type, data = publisher.messages[0]
    assert event_type == "usuario.creado"
    assert set(data) == {"empleadoId", "email", "tokenActivacion", "expiraEn"}
    assert validate_reset(data["tokenActivacion"], SECRET)["sub"] == "E001"
    assert repo.get_by_id("E001").status == INACTIVE
    with app_for(repo, publisher=publisher) as client:
        assert client.post("/auth/reset-password", json={"token": data["tokenActivacion"], "newPassword": NEW}).status_code == 200
        assert publisher.messages[-1] == ("cuenta.activada", {"empleadoId": "E001", "email": "ana@example.test", "motivo": "ACTIVACION_INICIAL"})
        response = client.post("/auth/recover-password", json={"email": "ana@example.test"})
        missing = client.post("/auth/recover-password", json={"email": "nobody@example.test"})
    assert response.status_code == missing.status_code == 202
    assert response.json() == missing.json()
    event_type, recovery = publisher.messages[-1]
    assert event_type == "usuario.recuperacion"
    assert set(recovery) == {"email", "tokenRecuperacion", "expiraEn"}
    assert validate_reset(recovery["tokenRecuperacion"], SECRET)["sub"] == "E001"


def test_catalog_vacation_retirement_sequence_never_reactivates_retired_account():
    repo, publisher = FakeRepository(), FakePublisher()
    processor = EventProcessor(repo, publisher, SECRET, 1800)
    processor.process(catalog_event("empleado.creado", created_data()))
    repo.set_password("E001", 0, hash_password(OLD))
    period = {"vacacionesId": "V001", "empleadoId": "E001", "email": "ana@example.test",
              "fechaInicio": "2026-10-04", "fechaFin": "2026-10-05"}
    start = catalog_event("vacaciones.iniciadas", period)
    assert processor.process(start)
    assert not processor.process(start)
    assert publisher.messages[-1] == ("cuenta.desactivada", {"empleadoId": "E001", "email": "ana@example.test",
                                                           "motivo": "VACACIONES", "permanente": False})
    retirement = {"empleadoId": "E001", "email": "ana@example.test",
                  "fechaRetiro": "2026-10-04T16:00:00Z", "motivo": "RENUNCIA"}
    assert processor.process(catalog_event("empleado.retirado", retirement))
    assert publisher.messages[-1][1]["permanente"] is True
    count = len(publisher.messages)
    assert not processor.process(catalog_event("vacaciones.finalizadas", {
        "vacacionesId": "V001", "empleadoId": "E001", "email": "ana@example.test", "fechaFin": "2026-10-05"}))
    assert repo.get_by_id("E001").status == RETIRED
    assert len(publisher.messages) == count


def test_catalog_vacation_finish_reactivates_active_employee_only():
    repo, publisher = FakeRepository(), FakePublisher()
    repo.add("E001", "ana@example.test")
    processor = EventProcessor(repo, publisher, SECRET, 1800)
    period = {"vacacionesId": "V001", "empleadoId": "E001", "email": "ana@example.test",
              "fechaInicio": "2026-10-04", "fechaFin": "2026-10-05"}
    assert processor.process(catalog_event("vacaciones.iniciadas", period))
    assert processor.process(catalog_event("vacaciones.finalizadas", {
        "vacacionesId": "V001", "empleadoId": "E001", "email": "ana@example.test", "fechaFin": "2026-10-05"}))
    assert repo.get_by_id("E001").status == ACTIVE
    assert publisher.messages[-1] == ("cuenta.activada", {"empleadoId": "E001", "email": "ana@example.test", "motivo": "FIN_VACACIONES"})


def test_outgoing_envelope_matches_catalog():
    from datetime import datetime, timezone
    event_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
    envelope = build_envelope("cuenta.activada", {"empleadoId": "E001", "email": "ana@example.test",
                                                    "motivo": "FIN_VACACIONES"}, event_id,
                              datetime(2026, 10, 4, 12, tzinfo=timezone.utc))
    assert set(envelope) == {"id", "type", "version", "occurredAt", "producer", "data"}
    assert envelope["id"] == str(event_id)
    assert envelope["producer"] == "auth-service"
    assert envelope["occurredAt"] == "2026-10-04T12:00:00.000Z"
