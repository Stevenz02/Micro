# Genera la configuracion local del proyecto (equivalente a setup-secrets.sh para Windows):
#   - .env                 (copia de .env.example: solo configuracion NO sensible)
#   - secrets\<nombre>.txt (Docker Compose Secrets con valores aleatorios; Git los ignora)
#
# Uso:   .\scripts\setup-secrets.ps1          # primera vez (no pisa secretos existentes)
#        .\scripts\setup-secrets.ps1 -Force   # ROTAR todos los secretos
# Tras rotar hay que recrear los datos: docker compose down -v ; docker compose up --build
# (Archivo solo con caracteres ASCII: Windows PowerShell 5.1 lo lee sin BOM.)
[CmdletBinding()]
param([switch]$Force)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot ".env"
$secretsPath = Join-Path $projectRoot "secrets"
$utf8 = New-Object System.Text.UTF8Encoding($false)

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker es obligatorio." }

if (-not (Test-Path -LiteralPath $envPath)) {
    Copy-Item -LiteralPath (Join-Path $projectRoot ".env.example") -Destination $envPath
    Write-Host ".env creado a partir de .env.example"
}

if ((Test-Path -LiteralPath (Join-Path $secretsPath "jwt_secret.txt")) -and -not $Force) {
    Write-Host "Los secretos ya existen en secrets\. Use -Force para rotarlos."
    return
}

function New-RandomSecret([int]$bytes = 32) {
    $buffer = New-Object byte[] $bytes
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($buffer) } finally { $generator.Dispose() }
    return [Convert]::ToBase64String($buffer).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}
function Set-Secret([string]$name, [string]$value) {
    [System.IO.File]::WriteAllText((Join-Path $secretsPath "$name.txt"), $value, $utf8)
}

New-Item -ItemType Directory -Force -Path $secretsPath | Out-Null

# El webhook de alertas no se genera: se conserva el que ya este configurado
$webhook = ""
$webhookFile = Join-Path $secretsPath "discord_webhook_url.txt"
if (Test-Path -LiteralPath $webhookFile) { $webhook = ([System.IO.File]::ReadAllText($webhookFile)).Trim() }
if (-not $webhook -and $env:DISCORD_WEBHOOK_URL) { $webhook = $env:DISCORD_WEBHOOK_URL.Trim() }

$adminPassword = New-RandomSecret 18
# El sistema solo guarda el hash bcrypt; la contrasena en claro queda unicamente en secrets\
$adminHash = docker run --rm -e "ADMIN_PASSWORD=$adminPassword" --mount "type=bind,source=$projectRoot,target=/work,readonly" -w /work python:3.12-alpine sh -c 'pip install --disable-pip-version-check -q bcrypt==4.3.0 >/dev/null 2>&1 && python scripts/hash_password.py'
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($adminHash) -or -not "$adminHash".Trim().StartsWith('$2')) {
    throw "No se pudo generar el hash bcrypt. Revise que Docker este iniciado y tenga red."
}

Set-Secret "jwt_secret" (New-RandomSecret 48)
Set-Secret "rabbitmq_password" (New-RandomSecret 32)
foreach ($db in "empleados", "departamentos", "perfiles", "notificaciones", "vacaciones", "auth") {
    Set-Secret "db_${db}_password" (New-RandomSecret 32)
}
Set-Secret "admin_password" $adminPassword
Set-Secret "admin_password_hash" "$adminHash".Trim()
Set-Secret "grafana_admin_password" (New-RandomSecret 24)
Set-Secret "jenkins_admin_password" (New-RandomSecret 24)
# SonarQube exige mayuscula, minuscula, numero y caracter especial: el sufijo lo garantiza
Set-Secret "sonar_admin_password" ((New-RandomSecret 24) + "_aA1")
Set-Secret "sonar_db_password" (New-RandomSecret 32)
Set-Secret "discord_webhook_url" $webhook

Write-Host "Secretos generados en secrets\ (15 archivos, ignorados por Git)."
Write-Host "  - Administrador semilla: usuario ADMIN_EMAIL de .env, contrasena en secrets\admin_password.txt"
if (-not $webhook) { Write-Host "  - Alertas: pegue la URL del webhook de Discord en secrets\discord_webhook_url.txt" }
Write-Host "Siguiente paso: docker compose up --build"
