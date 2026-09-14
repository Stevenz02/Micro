$BaseUrl = "http://localhost:8080"
Add-Type -AssemblyName System.Net.Http
$Cliente = New-Object System.Net.Http.HttpClient

$Empleado = @{
    id = "E001"
    nombre = "Juan"
    apellido = "Perez"
    email = "juan.perez@empresa.com"
    numeroEmpleado = "EMP-2026-001"
    cargo = "Desarrollador Senior"
    area = "Tecnologia"
    departamentoId = "IT"
    fechaIngreso = "2026-02-10"
    estado = "ACTIVO"
}

function Invoke-Prueba {
    param(
        [string]$Nombre,
        [string]$Metodo,
        [string]$Ruta,
        [int]$CodigoEsperado,
        [object]$Body = $null,
        [string]$TextoEsperado = ""
    )

    $MetodoHttp = New-Object System.Net.Http.HttpMethod($Metodo)
    $Solicitud = New-Object System.Net.Http.HttpRequestMessage(
        $MetodoHttp,
        "$BaseUrl$Ruta"
    )
    if ($null -ne $Body) {
        $Json = $Body | ConvertTo-Json -Depth 5
        $Solicitud.Content = New-Object System.Net.Http.StringContent(
            $Json,
            [System.Text.Encoding]::UTF8,
            "application/json"
        )
    }

    try {
        $Respuesta = $Cliente.SendAsync($Solicitud).GetAwaiter().GetResult()
        $Codigo = [int]$Respuesta.StatusCode
        $Contenido = $Respuesta.Content.ReadAsStringAsync().GetAwaiter().GetResult()
    }
    finally {
        if ($null -ne $Respuesta) { $Respuesta.Dispose() }
        $Solicitud.Dispose()
    }

    $CumpleCodigo = $Codigo -eq $CodigoEsperado
    $CumpleTexto = !$TextoEsperado -or $Contenido.Contains($TextoEsperado)
    $Resultado = if ($CumpleCodigo -and $CumpleTexto) { "OK" } else { "FALLO" }
    $DetalleEsperado = if ($TextoEsperado) {
        ", contiene '$TextoEsperado'"
    } else {
        ""
    }

    Write-Host "`nPrueba: $Nombre"
    Write-Host "Codigo HTTP: $Codigo"
    Write-Host "Body: $Contenido"
    Write-Host "Resultado esperado: HTTP $CodigoEsperado$DetalleEsperado"
    Write-Host "Resultado: $Resultado"
}

Invoke-Prueba "POST empleado E001" "POST" "/empleados" 200 $Empleado '"id":"E001"'
Invoke-Prueba "GET empleado E001" "GET" "/empleados/E001" 200 $null '"id":"E001"'
Invoke-Prueba "GET empleado E999" "GET" "/empleados/E999" 404 $null "El empleado con id E999 no existe"

$EmailDuplicado = $Empleado.Clone()
$EmailDuplicado.id = "E002"
$EmailDuplicado.numeroEmpleado = "EMP-2026-002"
Invoke-Prueba "Email duplicado" "POST" "/empleados" 400 $EmailDuplicado "email"

$NumeroDuplicado = $Empleado.Clone()
$NumeroDuplicado.id = "E003"
$NumeroDuplicado.email = "otro@empresa.com"
Invoke-Prueba "Numero de empleado duplicado" "POST" "/empleados" 400 $NumeroDuplicado "empleado"

Invoke-Prueba "Ruta inexistente" "GET" "/ruta-inexistente" 404 $null "Recurso no encontrado"
Invoke-Prueba "DELETE no soportado" "DELETE" "/empleados/E001" 404 $null "Recurso no encontrado"

$Cliente.Dispose()
