# Configuraciones SonarScanner CLI

Estos archivos se evalúan desde la raíz del monorepo. Los proyectos Java y Python/Node/Go
usan `sonar-scanner -Dproject.settings=<archivo>`. Vacaciones utiliza SonarScanner for .NET,
porque el scanner genérico no analiza C# correctamente; su clave y rutas se declaran en
`Reto_7/jenkins/Jenkinsfile.vacaciones`.

Las credenciales y `sonar.host.url` se inyectan mediante `withSonarQubeEnv`; ningún token se
almacena aquí.
