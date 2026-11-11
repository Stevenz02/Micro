[CmdletBinding()]
param(
    [string]$AdminEmail = "admin@proyecto.local",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot ".env"
$secretsPath = Join-Path $projectRoot "secrets"

if ((Test-Path -LiteralPath $envPath) -and -not $Force) {
    throw "Ya existe $envPath. Use -Force solo si desea rotar todas las credenciales locales."
}

function New-RandomSecret([int]$bytes = 32) {
    $buffer = New-Object byte[] $bytes
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($buffer) } finally { $generator.Dispose() }
    return [Convert]::ToBase64String($buffer).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker es necesario para generar el hash bcrypt y ejecutar el proyecto."
}

$adminPassword = New-RandomSecret 18
$bcrypt = docker run --rm -e "ADMIN_PASSWORD=$adminPassword" --mount "type=bind,source=$projectRoot,target=/work" -w /work python:3.12-alpine sh -c 'pip install --disable-pip-version-check -q bcrypt==4.3.0 && python scripts/hash_password.py'
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($bcrypt)) {
    throw "No se pudo generar ADMIN_PASSWORD_HASH. Revise que Docker esté iniciado."
}
$composeBcrypt = $bcrypt.Trim().Replace('$', '$$')

$values = [ordered]@{
    GATEWAY_PORT = "8080"; GRAFANA_PORT = "3000"; PROMETHEUS_PORT = "9091"; ZIPKIN_PORT = "9411"
    RABBITMQ_MANAGEMENT_PORT = "15672"; JENKINS_PORT = "8090"; JENKINS_AGENT_PORT = "50000"; SONAR_PORT = "9000"; REGISTRY_PORT = "5001"
    JWT_SECRET = (New-RandomSecret); RABBITMQ_USER = "rrhh"; RABBITMQ_PASSWORD = (New-RandomSecret)
    GRAFANA_ADMIN_USER = "admin"; GRAFANA_ADMIN_PASSWORD = (New-RandomSecret)
    JENKINS_ADMIN_ID = "admin"; JENKINS_ADMIN_PASSWORD = (New-RandomSecret)
    SONAR_ADMIN_PASSWORD = (New-RandomSecret); SONAR_DB_PASSWORD = (New-RandomSecret)
    E2E_ADMIN_EMAIL = $AdminEmail; E2E_ADMIN_PASSWORD = $adminPassword
    ADMIN_EMPLOYEE_ID = "00000000-0000-0000-0000-000000000001"; ADMIN_EMAIL = $AdminEmail; ADMIN_PASSWORD_HASH = $composeBcrypt
    DISCORD_WEBHOOK_URL = ""
    DB_EMPLEADOS_NAME = "empleados"; DB_EMPLEADOS_USER = "empleados"; DB_EMPLEADOS_PASSWORD = (New-RandomSecret)
    DB_DEPARTAMENTOS_NAME = "departamentos"; DB_DEPARTAMENTOS_USER = "departamentos"; DB_DEPARTAMENTOS_PASSWORD = (New-RandomSecret)
    DB_PERFILES_NAME = "perfiles"; DB_PERFILES_USER = "perfiles"; DB_PERFILES_PASSWORD = (New-RandomSecret)
    DB_NOTIFICACIONES_NAME = "notificaciones"; DB_NOTIFICACIONES_USER = "notificaciones"; DB_NOTIFICACIONES_PASSWORD = (New-RandomSecret)
    DB_VACACIONES_NAME = "vacaciones"; DB_VACACIONES_USER = "vacaciones"; DB_VACACIONES_PASSWORD = (New-RandomSecret)
    DB_AUTH_NAME = "auth"; DB_AUTH_USER = "auth"; DB_AUTH_PASSWORD = (New-RandomSecret)
    JWT_ACCESS_TTL_SECONDS = "900"; JWT_RESET_TTL_SECONDS = "1800"; GATEWAY_REQUEST_TIMEOUT_SECONDS = "20"
    VACACIONES_SCHEDULER_INTERVAL_SECONDS = "5"; DEPARTAMENTOS_TIMEOUT_SECONDS = "2"; DEPARTAMENTOS_MAX_RETRIES = "3"
    DEPARTAMENTOS_BACKOFF_SECONDS = "1"; DEPARTAMENTOS_CB_FAIL_MAX = "3"; DEPARTAMENTOS_CB_RESET_TIMEOUT_SECONDS = "30"
    PENDIENTES_RECONCILIATION_INTERVAL_SECONDS = "15"; POLL_TIMEOUT_SECONDS = "30"; POLL_INTERVAL_MS = "500"
    POLL_MAX_ATTEMPTS = "60"; HTTP_TIMEOUT_SECONDS = "20"; CHAOS_EMPLEADOS_LATENCY_SECONDS = "0"
    CHAOS_DEPARTAMENTOS_LATENCY_SECONDS = "0"; CHAOS_LATENCY_PROBABILITY = "0.5"
    SONAR_MIN_COVERAGE = "70"; SONARQUBE_IMAGE = "sonarqube:community"; REPO_URL = "file:///repo"; REPO_BRANCH = "*/main"
}

$lines = $values.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }
[System.IO.File]::WriteAllLines($envPath, $lines, [System.Text.UTF8Encoding]::new($false))
New-Item -ItemType Directory -Force -Path $secretsPath | Out-Null
[System.IO.File]::WriteAllText((Join-Path $secretsPath "admin-password.txt"), $adminPassword, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText((Join-Path $secretsPath "README.txt"), "Credenciales locales generadas. Esta carpeta está ignorada por Git.", [System.Text.UTF8Encoding]::new($false))

Write-Host "Configuración local creada en $envPath"
Write-Host "La contraseña del ADMIN se guardó en secrets/admin-password.txt (no versionado)."
Write-Host "Siguiente paso: docker compose up --build -d --wait --wait-timeout 600"
