$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = 'python' }
$reports = Join-Path $root 'Reto_5\auth\reports'
$env:COVERAGE_FILE = Join-Path $reports '.coverage'
New-Item -ItemType Directory -Force -Path $reports | Out-Null
Push-Location $root
try {
    & $python -m pytest Reto_5/tests/test_auth.py `
        --cov=auth_app.passwords --cov=auth_app.lifecycle `
        --cov=shared.tokens --cov-report="xml:$reports\coverage.xml" `
        --junitxml="$reports\junit.xml"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally { Pop-Location }
