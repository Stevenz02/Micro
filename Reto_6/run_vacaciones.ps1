$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$project = Join-Path $root 'Reto_5\vacaciones.tests\Vacaciones.Tests.csproj'
$reports = Join-Path $root 'Reto_5\vacaciones.tests\reports'
New-Item -ItemType Directory -Force -Path $reports | Out-Null
$started = Get-Date
dotnet test $project --collect:'XPlat Code Coverage' --results-directory $reports `
    --logger 'trx;LogFileName=vacaciones.trx'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$coverage = Get-ChildItem $reports -Recurse -Filter 'coverage.cobertura.xml' |
    Where-Object { $_.LastWriteTime -ge $started.AddSeconds(-2) } |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $coverage) { throw 'No se generó coverage.cobertura.xml' }
Copy-Item -LiteralPath $coverage.FullName -Destination (Join-Path $reports 'coverage.xml') -Force
