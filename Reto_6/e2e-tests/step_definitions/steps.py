"""Pasos Gherkin en español, ejecutados únicamente por HTTP contra el Gateway."""

from datetime import datetime, timedelta, timezone

from behave import given, when, then

from support.test_data import employee, unique_suffix


def state(context):
    return context.state


def current(context):
    value = state(context)
    return value.current_token or value.admin()


@when("consulto la salud del Gateway")
def health(context):
    state(context).send("GET", "/health")


@then("la respuesta debe tener código {code:d}")
def status(context, code):
    response = state(context).response
    assert response is not None, "No hay respuesta HTTP para verificar"
    assert response.status_code == code, (
        f"Esperaba HTTP {code}, obtuvo {response.status_code}: {response.text[:600]}"
    )


@then("la respuesta indica que el Gateway está operativo")
def health_body(context):
    assert state(context).response.json() == {"status": "ok", "service": "api-gateway"}


@given('que actúo como "{role}"')
def as_role(context, role):
    value = state(context)
    if role == "ADMIN":
        value.current_token = value.admin()
    elif role == "USER":
        value.current_token = value.user_token or value.activate_employee()
    else:
        raise AssertionError(f"Rol de prueba desconocido: {role}")
    value.current_role = role


@given("que existe un empleado registrado")
def registered(context):
    state(context).create_employee()


@given("que existe un empleado registrado con token de activación")
def registered_with_token(context):
    value = state(context)
    value.create_employee()
    value.get_activation_token()


@given("que existe un empleado activo con credenciales establecidas")
def active(context):
    value = state(context)
    value.activate_employee()
    value.current_token = value.admin()
    value.current_role = "ADMIN"


@when("consulto empleados sin token")
def employees_without_token(context):
    state(context).send("GET", "/empleados")


@when("consulto empleados con un token malformado")
def employees_bad_token(context):
    state(context).send("GET", "/empleados", token="token-invalido")


@when("consulto empleados con la firma alterada")
def employees_tampered(context):
    value = state(context)
    value.send("GET", "/empleados", token=value.admin() + "alterado")


@when("consulto empleados con el token de activación")
def employees_with_activation(context):
    value = state(context)
    value.send("GET", "/empleados", token=value.activation_token)


@when("consulto empleados")
def employees(context):
    state(context).send("GET", "/empleados", token=current(context))


@when("intento crear otro empleado")
def user_create(context):
    value = state(context)
    other = employee(unique_suffix(), value.department_id)
    value.send("POST", "/empleados", token=value.current_token, body=other)


@when("intento retirar mi empleado")
def user_retire(context):
    value = state(context)
    value.send("DELETE", f"/empleados/{value.employee['id']}?motivo=RENUNCIA", token=value.current_token)


@when("actualizo mi perfil")
def own_profile(context):
    value = state(context)
    employee_id = value.employee["id"]
    value.wait(lambda: value.gateway.request("GET", f"/perfiles/{employee_id}", token=value.admin()).status_code == 200,
               "proyección de perfil")
    value.send("PUT", f"/perfiles/{employee_id}", token=value.current_token, body={
        "telefono": "3001234567", "direccion": "Calle 1", "ciudad": "Armenia", "biografia": "Prueba E2E",
    })


@when("intento actualizar otro perfil")
def other_profile(context):
    value = state(context)
    value.send("PUT", f"/perfiles/OTRO-{value.suffix}", token=value.current_token, body={
        "telefono": "1", "direccion": "X", "ciudad": "X", "biografia": "X",
    })


@when("consulto el token de seguridad falsificando el rol ADMIN")
def spoofed_role(context):
    value = state(context)
    note = value.wait_notification("SEGURIDAD", "Cuenta creada")
    value.send("GET", f"/notificaciones/seguridad/{note['id']}/token",
               token=value.current_token, headers={"X-Authenticated-Role": "ADMIN",
                                                   "X-Authenticated-Employee-Id": "ADMIN"})


@when("consulto el token simulado de seguridad")
def admin_security_token(context):
    value = state(context)
    note = value.wait_notification("SEGURIDAD", "Cuenta creada")
    value.send("GET", f"/notificaciones/seguridad/{note['id']}/token", token=value.admin())


@then("la respuesta contiene el token de activación")
def token_matches(context):
    value = state(context)
    assert value.response.json()["token"] == value.activation_token


@when("registro un empleado único")
def register(context):
    state(context).create_employee()


@then("eventualmente se registra la traza de alta del empleado")
def trace_created(context):
    state(context).wait_notification("ALTA", "Alta de empleado")


@then("eventualmente aparece el token de activación en una notificación de seguridad")
def activation_note(context):
    assert state(context).get_activation_token()


@then("el empleado registrado tiene los datos solicitados")
def employee_readback(context):
    value = state(context)
    response = value.gateway.request("GET", f"/empleados/{value.employee['id']}", token=value.admin())
    value.expect(response, 200, "Leer empleado registrado")
    assert response.json()["email"] == value.employee["email"]
    assert response.json()["numeroEmpleado"] == value.employee["numeroEmpleado"]


@when("establece su contraseña con el token")
def set_password(context):
    value = state(context)
    value.send("POST", "/auth/reset-password", body={
        "token": value.activation_token, "newPassword": value.password,
    })


@then("eventualmente inicia sesión con la nueva contraseña")
def login_new(context):
    value = state(context)
    response = value.wait(value._successful_user_login, "login tras activación")
    value.user_token = response.json()["access_token"]


@then("eventualmente se notifica la activación inicial")
def activation_logged(context):
    state(context).wait_notification("CUENTA", "ACTIVACION_INICIAL")


@when("intenta reutilizar el token de activación")
def reuse_token(context):
    value = state(context)
    value.send("POST", "/auth/reset-password", body={
        "token": value.activation_token, "newPassword": value.password,
    })


@when("registro un empleado en un departamento inexistente")
def invalid_department(context):
    value = state(context)
    value.send("POST", "/empleados", token=value.admin(),
               body=employee(value.suffix, f"NOEXISTE-{value.suffix}"))


@when("registro un empleado sin apellido")
def missing_last_name(context):
    value = state(context)
    data = employee(value.suffix, value.create_department())
    del data["apellido"]
    value.send("POST", "/empleados", token=value.admin(), body=data)


@when('registro otro empleado con el mismo "{field}"')
def duplicate(context, field):
    value = state(context)
    assert field in {"email", "numeroEmpleado"}
    data = employee(unique_suffix(), value.department_id)
    data[field] = value.employee[field]
    value.send("POST", "/empleados", token=value.admin(), body=data)


@when("actualizo el cargo del empleado")
def update_employee(context):
    value = state(context)
    update = {key: val for key, val in value.employee.items() if key not in {"id", "estado"}}
    update["cargo"] = "Líder de Calidad"
    value.send("PUT", f"/empleados/{value.employee['id']}", token=value.admin(), body=update)
    assert value.response.status_code != 200 or value.response.json()["cargo"] == "Líder de Calidad"


@when("retiro el empleado")
def retire(context):
    value = state(context)
    value.send("DELETE", f"/empleados/{value.employee['id']}?motivo=RENUNCIA", token=value.admin())


@then("el empleado queda conservado con estado RETIRADO")
def retired_readback(context):
    value = state(context)
    response = value.gateway.request("GET", f"/empleados/{value.employee['id']}", token=value.admin())
    value.expect(response, 200, "Auditoría de empleado retirado")
    assert response.json()["estado"] == "RETIRADO"
    assert response.json()["fechaRetiro"] is not None


@then("aparece en la consulta de auditoría")
def audit_filter(context):
    value = state(context)
    response = value.gateway.request("GET", "/empleados?estado=RETIRADO", token=value.admin())
    value.expect(response, 200, "Consultar empleados retirados")
    assert value.employee["id"] in {item["id"] for item in response.json()}


@then("eventualmente se registra la traza de retiro")
def retirement_trace(context):
    state(context).wait_notification("RETIRO", "Retiro de empleado")


@then("eventualmente se notifica la desactivación permanente")
def permanent_note(context):
    state(context).wait_notification("CUENTA", "RETIRO")


@when("programo vacaciones futuras")
def future_vacation(context):
    value = state(context)
    start, end = value.future_dates()
    result = value.schedule(start, end)
    if result.status_code == 201:
        value.vacation_id = result.json()["id"]


@when("programo vacaciones para hoy")
def today_vacation(context):
    value = state(context)
    today = value.utc_today()
    result = value.schedule(today, today)
    if result.status_code == 201:
        value.vacation_id = result.json()["id"]


@when("programo vacaciones con fecha final anterior al inicio")
def end_before_start(context):
    value = state(context)
    start, _ = value.future_dates()
    value.schedule(start, value.utc_today())


@when("programo vacaciones en el pasado")
def past_vacation(context):
    value = state(context)
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    value.schedule(yesterday, value.utc_today())


@given("que tiene vacaciones futuras programadas")
def existing_vacation(context):
    value = state(context)
    start, end = value.future_dates()
    value.expect(value.schedule(start, end), 201, "Programar primera vacación")
    value.vacation_id = value.response.json()["id"]


@when("programo vacaciones que se solapan")
def overlapping_vacation(context):
    value = state(context)
    start, end = value.future_dates(offset=11, length=2)
    value.schedule(start, end)


@then("no aparece un período adicional para el empleado")
def only_one_vacation(context):
    value = state(context)
    response = value.gateway.request("GET", f"/vacaciones?empleadoId={value.employee['id']}", token=value.admin())
    value.expect(response, 200, "Listar vacaciones")
    assert [item["id"] for item in response.json()] == [value.vacation_id]


@then("eventualmente se notifica la programación de vacaciones")
def scheduled_note(context):
    state(context).wait_notification("VACACIONES", "Vacaciones programadas")


@then("eventualmente se notifica la suspensión por vacaciones")
def suspension(context):
    value = state(context)
    value.wait_notification("VACACIONES", "Vacaciones iniciadas")
    value.wait_notification("CUENTA", "VACACIONES")


@then("eventualmente se notifica el fin de vacaciones")
def finished(context):
    value = state(context)
    value.wait_notification("VACACIONES", "Vacaciones finalizadas")


@then("el empleado no puede iniciar sesión")
def login_blocked(context):
    value = state(context)
    response = value.login(value.employee["email"], value.password)
    value.expect(response, 401, "Login de empleado suspendido o retirado")


@then("eventualmente el empleado vuelve a iniciar sesión")
def login_restored(context):
    value = state(context)
    value.wait_notification("CUENTA", "FIN_VACACIONES")
    response = value.wait(value._successful_user_login, "login tras vacaciones")
    assert response.json()["access_token"]


@when("solicita recuperar su contraseña después del retiro")
def recover_retired(context):
    value = state(context)
    value.security_ids_before = {item["id"] for item in value.notifications() if item["tipo"] == "SEGURIDAD"}
    value.send("POST", "/auth/recover-password", body={"email": value.employee["email"]})


@then("recibe la respuesta genérica de recuperación")
def generic_recovery(context):
    response = state(context).response
    assert response.status_code == 202, f"Esperaba 202, obtuvo {response.status_code}: {response.text}"
    assert response.json()["detail"] == "Si la cuenta existe, recibirá instrucciones de recuperación"


@then("no se genera un nuevo token de recuperación")
def no_recovery_note(context):
    value = state(context)
    # Observación acotada: la API protege la existencia de la cuenta devolviendo 202.
    def new_security_note():
        return any(item["tipo"] == "SEGURIDAD" and item["id"] not in value.security_ids_before
                   for item in value.notifications())
    try:
        value.wait(new_security_note, "nuevo token para cuenta retirada", timeout=3)
    except AssertionError:
        return
    raise AssertionError("Se publicó un token de recuperación para una cuenta retirada")
