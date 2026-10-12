param([ValidateSet('Unit','Integration','All')][string]$Suite = 'All')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = 'python' }
$reports = Join-Path $root 'Reto_4\empleados\reports'
$env:COVERAGE_FILE = Join-Path $reports '.coverage'
New-Item -ItemType Directory -Force -Path $reports | Out-Null
Push-Location $root
try {
    if ($Suite -in @('Unit','All')) {
        & $python -m pytest Reto_4/tests -m 'not integration' `
            --cov=Reto_4.empleados.app.main --cov=Reto_4.empleados.app.models `
            --cov=Reto_4.empleados.app.events --cov-report="xml:$reports\coverage.xml" `
            --junitxml="$reports\junit.xml"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    if ($Suite -in @('Integration','All')) {
        & $python -m pytest Reto_4/tests/test_empleados_integration.py -m integration `
            --junitxml="$reports\junit-integration.xml"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
} finally { Pop-Location }
