# Verificacion Reto 3

Este documento separa las pruebas unitarias sin Docker y la verificacion runtime
con Docker Compose. En el estado actual ambas partes estan implementadas.

## A. Verificacion unitaria sin Docker

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

## Cobertura unitaria

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
| OPEN tras fallos | CUMPLE | `test_despues_de_tres_fallos...` |
| OPEN no llama HTTP | CUMPLE | `test_despues_de_tres_fallos...` |
| HALF_OPEN -> CLOSED | CUMPLE | `test_half_open_exitoso...` |
| HALF_OPEN -> OPEN | CUMPLE | `test_half_open_fallido...` |
| 404 no abre circuito | CUMPLE | `test_departamento_inexistente...` |

## B. Verificacion con Docker Compose

Preparar variables y levantar:

```powershell
Set-Location D:\Repositorios_UQ\Micro\Reto_3
Copy-Item .env.example .env
docker compose up -d --build --wait --wait-timeout 180
docker compose ps
```

Verificar punto unico de entrada:

```powershell
curl http://localhost:8080/health
curl http://localhost:8080/departamentos
curl http://localhost:8080/empleados
curl http://localhost:8081/empleados
curl http://localhost:8082/departamentos
```

Resultado esperado:

```text
localhost:8080 responde por Gateway.
localhost:8081 falla por conexion rechazada.
localhost:8082 falla por conexion rechazada.
```

Crear departamento por Gateway:

```powershell
Invoke-WebRequest -Uri http://localhost:8080/departamentos -Method POST `
  -ContentType "application/json" `
  -Body '{"id":"IT","nombre":"Tecnologia","descripcion":"Tecnologia"}'
```

Probar apertura del Circuit Breaker:

```powershell
docker compose stop departamentos-service

for ($i=1; $i -le 8; $i++) {
  $body = @{
    id="E10$i"; nombre="Test $i"; apellido="T"; email="test$i@x.com"
    numeroEmpleado="N10$i"; cargo="Dev"; area="IT"; departamentoId="IT"
    fechaIngreso="2026-01-01"; estado="ACTIVO"
  } | ConvertTo-Json
  Measure-Command {
    try { Invoke-RestMethod -Uri http://localhost:8080/empleados -Method POST -ContentType "application/json" -Body $body }
    catch { Write-Host "Error: $($_.Exception.Response.StatusCode)" }
  } | Select-Object TotalSeconds
}
```

Resultado observado y documentado en `README.md`:

```text
Peticion 1: ~19.3 segundos, agotando reintentos.
Peticiones 2-8: ~0.03 segundos, fallback inmediato por circuito OPEN.
```

Probar recuperacion automatica:

```powershell
docker compose start departamentos-service
Start-Sleep -Seconds 35

Invoke-RestMethod -Uri http://localhost:8080/empleados -Method POST -ContentType "application/json" -Body (@{
  id="E201"; nombre="Recuperado"; apellido="T"; email="e201@x.com"
  numeroEmpleado="N201"; cargo="Dev"; area="IT"; departamentoId="NO-EXISTE"
  fechaIngreso="2026-01-01"; estado="ACTIVO"
} | ConvertTo-Json)
```

Resultado esperado:

```text
400: El departamento con id NO-EXISTE no existe
```

Ese 400 confirma que el Circuit Breaker dejo de crear pendientes por fallback,
paso por HALF_OPEN y volvio a CLOSED consultando realmente a departamentos.
