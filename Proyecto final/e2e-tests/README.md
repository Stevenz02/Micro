# Suite BDD independiente

Instale `requirements.txt`, copie `.env.example` a `.env`, configure `ADMIN_EMAIL` y `ADMIN_PASSWORD`, y ejecute `python run.py` desde esta carpeta con el Reto 5 desplegado. `BASE_URL` indica la URL del Gateway; dentro de Docker puede ser `http://api-gateway:8080`. El runner conserva el código de salida de Behave y genera `reports/junit.xml`, `reports/cucumber.json` y `reports/cucumber.html`. Consulte `../README.md` para contratos, preparación del scheduler, escenarios y tabla completa de reportes.
