"""Transiciones de cuenta independientes del formato del Catálogo de Eventos."""

from dataclasses import dataclass

from shared.tokens import issue_reset

from .repository import ACTIVE, INACTIVE, RETIRED, SUSPENDED, next_status


@dataclass(frozen=True)
class Transition:
    changed: bool
    account: object | None = None
    reset_token: str | None = None


class AccountLifecycle:
    def __init__(self, repository, secret: str, reset_ttl_seconds: int):
        self.repository = repository
        self.secret = secret
        self.reset_ttl_seconds = reset_ttl_seconds

    def employee_created(self, employee_id: str, email: str) -> Transition:
        account = self.repository.create_employee(employee_id, email)
        if account is None:
            return Transition(False)
        token = issue_reset(self.secret, employee_id, account.credential_version, self.reset_ttl_seconds)
        return Transition(True, account, token)

    def employee_retired(self, employee_id: str) -> Transition:
        account = self.repository.transition(employee_id, (INACTIVE, ACTIVE, SUSPENDED), RETIRED)
        return Transition(account is not None, account)

    def vacation_started(self, employee_id: str) -> Transition:
        account = self.repository.transition(employee_id, (INACTIVE, ACTIVE), SUSPENDED)
        return Transition(account is not None, account)

    def vacation_finished(self, employee_id: str) -> Transition:
        current = self.repository.get_by_id(employee_id)
        status = next_status(current.status, current.password_hash, "vacaciones.finalizadas") if current else None
        account = self.repository.transition(employee_id, (SUSPENDED,), status) if status else None
        return Transition(account is not None, account)
