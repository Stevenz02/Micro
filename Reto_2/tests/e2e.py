"""Prueba real y aislada: crea y elimina SOLO sus propios volúmenes Compose.

Desde la raíz: python Reto_2/tests/e2e.py
Requiere Docker Compose; solo usa biblioteca estándar de Python.
"""
import concurrent.futures
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import uuid

ROOT = Path(__file__).resolve().parents[1]
PROJECT = f"micro-reto2-e2e-{uuid.uuid4().hex[:8]}"
ENV = os.environ.copy()
# Prueba los valores de demostración de Compose sin un .env ni credenciales
# heredadas del host, tal como sucede al clonar en otra máquina.
for name in list(ENV):
    if name.startswith(('DB_EMPLEADOS_', 'DB_DEPARTAMENTOS_')):
        ENV.pop(name)


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


EMP_PORT, DEP_PORT = free_port(), free_port()
while DEP_PORT == EMP_PORT:
    DEP_PORT = free_port()
ENV.update(EMPLEADOS_PORT=str(EMP_PORT), DEPARTAMENTOS_PORT=str(DEP_PORT),
           DEPARTAMENTOS_SERVICE_URL='http://departamentos-service:8081',
           DEPARTAMENTOS_TIMEOUT_SECONDS='2', DEPARTAMENTOS_MAX_RETRIES='3',
           DEPARTAMENTOS_BACKOFF_SECONDS='1')


def compose(*args, capture=False):
    print(f'[{PROJECT}] docker compose {" ".join(args)}', flush=True)
    result = subprocess.run(
        ['docker', 'compose', '--env-file', os.devnull, '-p', PROJECT, *args],
        cwd=ROOT, env=ENV, text=True, encoding='utf-8', errors='replace',
        capture_output=capture, check=True, timeout=600,
    )
    return result.stdout if capture else ''


def request(port, path, status=200, body=None):
    payload = json.dumps(body).encode() if body is not None else None
    req = Request(f'http://127.0.0.1:{port}{path}', data=payload,
                  headers={'Content-Type': 'application/json'})
    try:
        response = urlopen(req, timeout=40)
    except HTTPError as error:
        response = error
    with response:
        data = response.read().decode()
        assert response.status == status, (path, response.status, status, data)
        return json.loads(data) if 'application/json' in response.headers.get('Content-Type', '') else data


def healthy():
    states = [json.loads(line) for line in compose('ps', '--format', 'json', capture=True).splitlines() if line]
    assert len(states) == 4, states
    assert all(row['State'] == 'running' and row['Health'] == 'healthy' for row in states), states
    compose('ps')


DEPARTMENT = {'id': 'IT', 'nombre': 'Tecnología', 'descripcion': 'Departamento de TI'}
EMPLOYEE = {
    'id': 'E001', 'nombre': 'Juan', 'apellido': 'Pérez', 'email': 'juan.perez@empresa.com',
    'numeroEmpleado': 'EMP-2026-001', 'cargo': 'Desarrollador Senior', 'area': 'Tecnología',
    'departamentoId': 'IT', 'fechaIngreso': '2026-02-10', 'estado': 'ACTIVO',
}
EMPLOYEE_REQUEST = {key: value for key, value in EMPLOYEE.items() if key != 'estado'}


def main():
    try:
        compose('up', '-d', '--build', '--wait', '--wait-timeout', '180')
        healthy()
        startup = compose('logs', '--no-color', capture=True)
        assert not re.search(r'Traceback|ECONNREFUSED|connection refused|FATAL:|ERROR:', startup, re.I), startup
        print('OK: arranque limpio y cuatro servicios healthy', flush=True)

        for port, resource in [(EMP_PORT, 'empleados'), (DEP_PORT, 'departamentos')]:
            assert request(port, f'/{resource}') == []
            assert 'swagger' in request(port, '/docs/').lower()
            spec = request(port, '/openapi.json')
            assert f'/{resource}' in spec['paths']
            assert {'200'} <= set(spec['paths'][f'/{resource}']['get']['responses'])
            assert {'201', '400', '500'} <= set(spec['paths'][f'/{resource}']['post']['responses'])
            assert {'200', '404'} <= set(spec['paths'][f'/{resource}/{{id}}']['get']['responses'])
        assert 'SwaggerUIBundle' in request(DEP_PORT, '/docs/swagger-ui-bundle.js')
        assert request(DEP_PORT, '/departamentos', 201, DEPARTMENT) == DEPARTMENT
        assert request(EMP_PORT, '/empleados', 201, EMPLOYEE_REQUEST) == EMPLOYEE
        assert request(DEP_PORT, '/departamentos/IT') == DEPARTMENT
        assert request(EMP_PORT, '/empleados/E001') == EMPLOYEE
        assert request(EMP_PORT, '/empleados') == [EMPLOYEE]
        request(EMP_PORT, '/empleados/missing', 404)
        request(DEP_PORT, '/departamentos/missing', 404)
        request(DEP_PORT, '/departamentos', 400, DEPARTMENT)

        assert 'email' in request(EMP_PORT, '/empleados', 400, {
            **EMPLOYEE_REQUEST, 'id': 'E002', 'departamentoId': 'MISSING',
        })['detail']
        assert 'número' in request(EMP_PORT, '/empleados', 400, {
            **EMPLOYEE_REQUEST, 'id': 'E003', 'email': 'otro@empresa.com', 'departamentoId': 'MISSING',
        })['detail']
        assert 'no existe' in request(EMP_PORT, '/empleados', 400, {
            **EMPLOYEE_REQUEST, 'id': 'E004', 'email': 'nuevo@empresa.com', 'numeroEmpleado': 'NUEVO', 'departamentoId': 'MISSING',
        })['detail']
        assert 'id' in request(EMP_PORT, '/empleados', 400, {
            **EMPLOYEE, 'email': 'id@empresa.com', 'numeroEmpleado': 'ID',
        })['detail']
        request(EMP_PORT, '/empleados', 422, {**EMPLOYEE, 'estado': 'INACTIVO'})
        assert request(EMP_PORT, '/empleados') == [EMPLOYEE]
        print('OK: Swagger, altas, consultas, diez campos, validaciones y orden', flush=True)

        # Concurrencia real: exactamente un alta para cada clave única.
        for key in ['email', 'numeroEmpleado', 'id']:
            def register(index):
                body = {**EMPLOYEE, 'id': f'{key}-{index}', 'email': f'{key}{index}@empresa.com',
                        'numeroEmpleado': f'{key}-{index}', key: f'race-{key}@empresa.com' if key == 'email' else f'race-{key}'}
                req = Request(f'http://127.0.0.1:{EMP_PORT}/empleados', data=json.dumps(body).encode(),
                              headers={'Content-Type': 'application/json'})
                try:
                    response = urlopen(req, timeout=30)
                except HTTPError as error:
                    response = error
                with response:
                    response.read()
                    return response.status
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                statuses = list(executor.map(register, range(8)))
            assert statuses.count(201) == 1 and statuses.count(400) == 7, statuses
        assert len(request(EMP_PORT, '/empleados')) == 4
        print('OK: 24 peticiones concurrentes; tres altas y 21 duplicados controlados', flush=True)

        compose('pause', 'departamentos-service')
        started = time.monotonic()
        try:
            request(EMP_PORT, '/empleados', 503, {
                **EMPLOYEE, 'id': 'FALLO', 'email': 'fallo@empresa.com', 'numeroEmpleado': 'FALLO',
            })
        finally:
            compose('unpause', 'departamentos-service')
        elapsed = time.monotonic() - started
        assert 14 <= elapsed < 35, elapsed
        request(EMP_PORT, '/empleados/FALLO', 404)
        logs = compose('logs', '--no-color', 'empleados-service', capture=True)
        for attempt, delay in [(1, '1.0'), (2, '2.0'), (3, '4.0')]:
            assert f'reintento {attempt} en {delay}s' in logs
        print(f'OK: timeout real, tres reintentos y 503 sin inserción ({elapsed:.1f}s)', flush=True)

        compose('down')
        compose('up', '-d', '--wait', '--wait-timeout', '180')
        assert request(EMP_PORT, '/empleados/E001') == EMPLOYEE
        assert request(DEP_PORT, '/departamentos/IT') == DEPARTMENT
        assert len(request(EMP_PORT, '/empleados')) == 4
        print('OK: down conserva empleados y departamentos completos', flush=True)

        compose('down', '-v')
        compose('up', '-d', '--build', '--wait', '--wait-timeout', '180')
        assert request(EMP_PORT, '/empleados') == []
        assert request(DEP_PORT, '/departamentos') == []
        request(EMP_PORT, '/empleados/E001', 404)
        request(DEP_PORT, '/departamentos/IT', 404)
        healthy()
        final_logs = compose('logs', '--no-color', capture=True)
        assert not re.search(r'Traceback|ECONNREFUSED|connection refused|FATAL:|ERROR:', final_logs, re.I), final_logs
        print('OK: down -v borra datos, reinicialización limpia y cuatro healthy', flush=True)
        print('E2E COMPLETO: todas las comprobaciones pasaron', flush=True)
    except Exception:
        compose('ps')
        compose('logs', '--no-color', '--tail', '100')
        raise
    finally:
        # PROJECT es generado por esta ejecución; nunca se limpia el proyecto del usuario.
        compose('down', '-v')


if __name__ == '__main__':
    main()
