# Guía: escalabilidad y resiliencia (demostraciones)

Comandos en PowerShell desde la carpeta del proyecto, con el sistema arriba.

```powershell
$pw = (Get-Content .\secrets\admin_password.txt -Raw).Trim()
$t = (Invoke-RestMethod -Method Post http://localhost:8080/auth/login -ContentType 'application/json' -Body (@{email='admin@proyecto.local';password=$pw} | ConvertTo-Json)).access_token
$h = @{Authorization="Bearer $t"}
```

## 1. El balanceador reparte el tráfico

Cada respuesta de Empleados y Departamentos trae la cabecera `X-Instance-Id` con la instancia
que la atendió:

```powershell
1..6 | % { (Invoke-WebRequest http://localhost:8080/empleados -Headers $h -UseBasicParsing).Headers['X-Instance-Id'] }
```

Deben alternarse dos valores. El panel <http://localhost:8088> muestra los servicios, sus
servidores y el estado del health check.

## 2. El sistema sigue atendiendo cuando cae una instancia

```powershell
docker stop proyecto-final-empleados-service-1
1..6 | % { (Invoke-WebRequest http://localhost:8080/empleados -Headers $h -UseBasicParsing).StatusCode }
docker start proyecto-final-empleados-service-1
```

Todas las respuestas son `200`: el health check retira la instancia caída y el reintento cubre
la petición que estaba en curso. En Grafana, el panel "Réplicas sanas" baja a 1 y la alerta
"Servicio Caído" se dispara para esa instancia.

## 3. Escalar a más réplicas

```powershell
docker compose up -d --scale empleados-service=3 --no-recreate
```

Traefik descubre la nueva réplica por las etiquetas de Docker y Prometheus por DNS, sin tocar
ninguna configuración.

## 4. Circuit Breaker con fallback

```powershell
docker compose stop departamentos-service
$e = @{id="E900";nombre="Luis";apellido="Mora";email="luis.mora@empresa.com";numeroEmpleado="EMP-900";cargo="Analista";area="TI";departamentoId="IT";fechaIngreso="2026-11-01"} | ConvertTo-Json
Invoke-WebRequest -Method Post http://localhost:8080/empleados -Headers $h -ContentType 'application/json' -Body $e -UseBasicParsing | Select StatusCode, Content
```

- Las primeras peticiones tardan unos segundos (reintentos con backoff exponencial) y responden
  **`202`** con `"estado":"PENDIENTE"`: ese es el fallback.
- Tras 3 fallos el circuito se abre y las siguientes responden `202` de inmediato, sin llamar a
  Departamentos. Cada réplica de Empleados tiene su propio circuito, así que con 2 réplicas hacen
  falta unas 6 peticiones para ver abiertos los dos (use un `id`, `email` y `numeroEmpleado`
  distintos en cada una).
- Estado del circuito de la réplica que responda:
  `Invoke-RestMethod http://localhost:8080/health/dependencies -Headers $h`.
- En los logs: `docker compose logs empleados-service | Select-String "Circuit Breaker"`.

```powershell
docker compose start departamentos-service
```

Pasados 30 s el circuito pasa a semiabierto y la reconciliación (cada 15 s) confirma el alta:
el empleado pasa a `ACTIVO` y recién entonces se publica `empleado.creado`.

## 5. Consumidores tolerantes a duplicados

En RabbitMQ Management (<http://localhost:15672> → *Exchanges* → `rrhh.events` → *Publish
message*), publique **dos veces** el mismo mensaje con *routing key* `vacaciones.programadas`:

```json
{"id":"11111111-2222-4333-8444-555555555555","type":"vacaciones.programadas","version":1,
 "occurredAt":"2026-11-12T15:00:00Z","producer":"vacaciones-service",
 "data":{"vacacionesId":"V-DEMO","empleadoId":"E001","email":"ana.rios@empresa.com",
         "fechaInicio":"2026-12-15","fechaFin":"2026-12-30","diasHabiles":12}}
```

La primera vez se crea una notificación y llega un correo a Mailpit. La segunda, el consumidor
registra `evento_duplicado` y no repite nada:

```powershell
docker compose logs notificaciones-service | Select-String "evento_duplicado"
```
