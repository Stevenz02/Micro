# Suite BDD (Behave)

25 escenarios en español (Gherkin) que recorren el ciclo de vida completo a través del API
Gateway: onboarding, seguridad (RBAC y propiedad del perfil), vacaciones y offboarding.

## Ejecución

- **En Jenkins**: el job `proyecto-final` la ejecuta en su última etapa contra el sistema desplegado.
- **Manual**, con el ecosistema arriba (PowerShell, desde la raíz del proyecto):

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r e2e-tests\requirements.txt
$env:BASE_URL = "http://localhost:8080"
$env:ADMIN_EMAIL = "admin@proyecto.local"
$env:ADMIN_PASSWORD = (Get-Content .\secrets\admin_password.txt -Raw).Trim()
.\.venv\Scripts\python e2e-tests\run.py
```

`BASE_URL` es la URL del Gateway (dentro de Docker: `http://api-gateway:8080`). Las credenciales
del administrador nunca se escriben en archivos versionados: salen de `secrets/admin_password.txt`.

El runner conserva el código de salida de Behave y genera `reports/junit.xml`,
`reports/cucumber.json` y `reports/cucumber.html` (no se versionan).

Las esperas de los efectos asíncronos usan *polling* acotado (`POLL_TIMEOUT_SECONDS`,
`POLL_INTERVAL_MS`, `POLL_MAX_ATTEMPTS`), nunca `sleep` fijo.
