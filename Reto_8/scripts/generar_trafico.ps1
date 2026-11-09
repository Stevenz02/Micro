# Reto 8 - Genera trafico real por el API Gateway para poblar metricas, trazas y logs.
#   .\scripts\generar_trafico.ps1                 # onboarding + 20 consultas + vacaciones (scheduler)
#   .\scripts\generar_trafico.ps1 -Consultas 100  # mas trafico (util durante la prueba de latencia)
param(
    [string]$Gateway = "http://localhost:8080",
    [string]$Email = "admin@empresa.com",
    [string]$Password = "AdminRrhh2026",
    [int]$Consultas = 20,
    [switch]$SinOnboarding
)
$ErrorActionPreference = "Stop"

function Invoke-Api($Method, $Path, $Body = $null) {
    $params = @{ Method = $Method; Uri = "$Gateway$Path"; Headers = $script:Headers; ContentType = "application/json"; TimeoutSec = 30 }
    if ($Body) { $params.Body = ($Body | ConvertTo-Json -Compress) }
    try { return Invoke-RestMethod @params }
    catch {
        $code = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { "sin respuesta" }
        Write-Host "  $Method $Path -> $code" -ForegroundColor Yellow
        return $null
    }
}

Write-Host "1) Login como ADMIN" -ForegroundColor Cyan
$login = Invoke-RestMethod -Method Post -Uri "$Gateway/auth/login" -ContentType "application/json" `
    -Body (@{ email = $Email; password = $Password } | ConvertTo-Json -Compress)
$script:Headers = @{ Authorization = "Bearer $($login.access_token)" }

if (-not $SinOnboarding) {
    $sufijo = Get-Date -Format "HHmmss"
    $id = "E$sufijo"
    Write-Host "2) Departamento IT (si ya existe responde 400, es normal)" -ForegroundColor Cyan
    Invoke-Api Post "/departamentos" @{ id = "IT"; nombre = "Tecnologia"; descripcion = "Departamento de TI" } | Out-Null

    Write-Host "3) Onboarding del empleado $id (gateway -> empleados -> departamentos -> RabbitMQ -> auth/perfiles/notificaciones/vacaciones)" -ForegroundColor Cyan
    $empleado = Invoke-Api Post "/empleados" @{
        id = $id; nombre = "Ana"; apellido = "Gomez"; email = "ana.$sufijo@empresa.com"
        numeroEmpleado = "EMP-$sufijo"; cargo = "Analista"; area = "Tecnologia"
        departamentoId = "IT"; fechaIngreso = (Get-Date -Format "yyyy-MM-dd")
    }
    if ($empleado) { Write-Host "   Empleado creado: $($empleado.id) estado=$($empleado.estado)" -ForegroundColor Green }

    Write-Host "4) Vacaciones que inician HOY para $id (el scheduler crea la traza raiz)" -ForegroundColor Cyan
    $hoy = Get-Date -Format "yyyy-MM-dd"
    $vacacion = $null
    for ($i = 0; $i -lt 15 -and -not $vacacion; $i++) {
        Start-Sleep -Seconds 2   # espera a que vacaciones-service reciba la replica del empleado
        $vacacion = Invoke-Api Post "/vacaciones" @{ empleadoId = $id; fechaInicio = $hoy; fechaFin = $hoy }
    }
    if ($vacacion) { Write-Host "   Vacacion $($vacacion.id) PROGRAMADA; en ~5 s el scheduler la inicia" -ForegroundColor Green }
}

Write-Host "5) $Consultas consultas de lectura por varios servicios" -ForegroundColor Cyan
for ($i = 1; $i -le $Consultas; $i++) {
    Invoke-Api Get "/empleados" | Out-Null
    Invoke-Api Get "/departamentos" | Out-Null
    Invoke-Api Get "/perfiles" | Out-Null
    Invoke-Api Get "/notificaciones" | Out-Null
    Invoke-Api Get "/vacaciones" | Out-Null
    Invoke-Api Get "/empleados/NO-EXISTE" | Out-Null   # 404 a proposito (panel de errores 4xx)
    Write-Progress -Activity "Consultas" -Status "$i de $Consultas" -PercentComplete ($i * 100 / $Consultas)
}
Write-Host "Listo. Revise Grafana (http://localhost:3000) y Zipkin (http://localhost:9411)." -ForegroundColor Green
