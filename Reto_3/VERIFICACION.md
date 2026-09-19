# Verificacion Reto 3

## A. Verificacion realizable ahora

Instalar dependencias Python:

```powershell
Set-Location D:\Repositorios_UQ\Micro
.\.venv\Scripts\python.exe -m pip install -r Reto_3/requirements-test.txt
```

Instalar dependencias Node:

```powershell
npm --prefix Reto_3/departamentos ci
```

Ejecutar pruebas Gateway y empleados:

```powershell
.\.venv\Scripts\python.exe -m pytest Reto_3/tests -q
```

Resultado obtenido:

```text
39 passed, 8 warnings in 0.75s
```

Ejecutar pruebas departamentos:

```powershell
npm --prefix Reto_3/departamentos test
```

Resultado obtenido:

```text
tests 12
pass 12
fail 0
```

Regresion Reto 1:

```powershell
Push-Location Reto_1
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
```

Resultado obtenido:

```text
15 passed, 1 warning in 0.39s
```

Regresion Reto 2 empleados:

```powershell
.\.venv\Scripts\python.exe -m pytest Reto_2/tests -q
```

Resultado obtenido:

```text
25 passed, 1 warning in 0.63s
```

Regresion Reto 2 departamentos:

```powershell
npm --prefix Reto_2/departamentos test
```

Resultado obtenido:

```text
tests 12
pass 12
fail 0
```

Chequeo de sintaxis Python:

```powershell
.\.venv\Scripts\python.exe -m compileall -q Reto_3
```

## Cobertura pre-Docker

| Criterio | Estado | Prueba |
| --- | --- | --- |
| Gateway `/health` | CUMPLE | `test_health_responde_desde_gateway` |
| GET/POST a empleados | CUMPLE | `test_proxy_preserva...` |
| GET/POST a departamentos | CUMPLE | `test_proxy_preserva...` |
| Query strings | CUMPLE | `test_proxy_preserva...` |
| Request body | CUMPLE | `test_proxy_preserva...` |
| Status code/backend body | CUMPLE | `test_propaga_status...` |
| 400/404/500 backend | CUMPLE | `test_propaga_status...` |
| Conexion imposible -> 503 | CUMPLE | `test_upstream_caido...` |
| Timeout -> 503 | CUMPLE | `test_upstream_caido...` |
| JSON estable sin stack trace | CUMPLE | `test_upstream_caido...` |
| Circuito inicialmente CLOSED | CUMPLE | `test_circuito_inicia...` |
| Departamento existente OK | CUMPLE | `test_circuito_inicia...` |
| Departamento inexistente 400 | CUMPLE | `test_departamento_inexistente...` |
| Fallos tecnicos contabilizados | CUMPLE | `test_despues_de_tres_fallos...` |
| OPEN tras 3 fallos | CUMPLE | `test_despues_de_tres_fallos...` |
| OPEN no llama HTTP | CUMPLE | `test_despues_de_tres_fallos...` |
| HALF_OPEN -> CLOSED | CUMPLE | `test_half_open_exitoso...` |
| HALF_OPEN -> OPEN | CUMPLE | `test_half_open_fallido...` |
| 404 no abre circuito | CUMPLE | `test_departamento_inexistente...` |

## B. Verificacion posterior a Docker

Estos casos quedan documentados, pero no ejecutados en esta fase:

```text
Gateway accesible por localhost:8080
acceso directo a empleados rechazado
acceso directo a departamentos rechazado
apagar departamentos
probar error 503 del Gateway
provocar apertura del Circuit Breaker
observar diferencia de tiempos
restaurar departamentos
esperar reset timeout
probar HALF_OPEN
comprobar recuperacion automatica
```

Comandos esperados cuando exista Compose:

```powershell
docker compose up -d --build --wait --wait-timeout 180
docker compose ps
Invoke-RestMethod http://localhost:8080/health
Invoke-RestMethod http://localhost:8080/empleados
Invoke-RestMethod http://localhost:8080/departamentos
Invoke-RestMethod http://localhost:8080/health/dependencies
```

Para la prueba de resiliencia:

```powershell
docker compose pause departamentos-service
# Enviar altas de empleados por Gateway hasta abrir circuito.
Invoke-RestMethod http://localhost:8080/health/dependencies
docker compose unpause departamentos-service
# Esperar DEPARTAMENTOS_CB_RESET_TIMEOUT_SECONDS y validar recuperacion.
```
