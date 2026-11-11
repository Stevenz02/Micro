# Reto 7 - Jenkins personalizado: plugins + cliente Docker + toolchains de los 7 servicios.
# Los Jenkinsfiles de Kevin usan `agent any` y llaman python3, npm/node, go, mvn, dotnet,
# sonar-scanner y dotnet sonarscanner directamente: por eso quedan instalados aquí.
FROM jenkins/jenkins:lts-jdk21

ARG NODE_VERSION=22.11.0
ARG GO_VERSION=1.23.4
ARG MAVEN_VERSION=3.9.9
ARG SONAR_SCANNER_VERSION=6.2.1.4610

# 1) Plugins (como usuario jenkins, que es como lo espera jenkins-plugin-cli)
USER jenkins
COPY --chown=jenkins:jenkins plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

USER root
ENV DEBIAN_FRONTEND=noninteractive

# 2) Paquetes base + cliente Docker y plugin compose desde el repositorio oficial de Docker
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl gnupg unzip xz-utils git \
        python3 python3-venv python3-pip gosu; \
    # .NET necesita ICU (globalización); el nombre del paquete cambia con la versión de Debian
    apt-get install -y --no-install-recommends "$(apt-cache search --names-only '^libicu[0-9]+$' | awk '{print $1}' | sort -V | tail -n1)"; \
    install -m 0755 -d /etc/apt/keyrings; \
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc; \
    chmod a+r /etc/apt/keyrings/docker.asc; \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        > /etc/apt/sources.list.d/docker.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin docker-buildx-plugin; \
    rm -rf /var/lib/apt/lists/*

# 3) Toolchains: Node 22, Go 1.23, Maven 3.9, SonarScanner CLI, .NET 8 + SonarScanner for .NET
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) NODE_ARCH=x64;   GO_ARCH=amd64; SS_ARCH=linux-x64 ;; \
      arm64) NODE_ARCH=arm64; GO_ARCH=arm64; SS_ARCH=linux-aarch64 ;; \
      *) echo "Arquitectura no soportada: $arch"; exit 1 ;; \
    esac; \
    curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz" | tar -xJ -C /opt; \
    ln -s "/opt/node-v${NODE_VERSION}-linux-${NODE_ARCH}" /opt/node; \
    curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-${GO_ARCH}.tar.gz" | tar -xz -C /opt; \
    curl -fsSL "https://archive.apache.org/dist/maven/maven-3/${MAVEN_VERSION}/binaries/apache-maven-${MAVEN_VERSION}-bin.tar.gz" | tar -xz -C /opt; \
    ln -s "/opt/apache-maven-${MAVEN_VERSION}" /opt/maven; \
    curl -fsSL -o /tmp/scanner.zip "https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-${SONAR_SCANNER_VERSION}-${SS_ARCH}.zip"; \
    unzip -q /tmp/scanner.zip -d /opt; rm /tmp/scanner.zip; \
    ln -s "/opt/sonar-scanner-${SONAR_SCANNER_VERSION}-${SS_ARCH}" /opt/sonar-scanner; \
    curl -fsSL -o /tmp/dotnet-install.sh https://dot.net/v1/dotnet-install.sh; \
    bash /tmp/dotnet-install.sh --channel 8.0 --install-dir /opt/dotnet; rm /tmp/dotnet-install.sh; \
    DOTNET_CLI_TELEMETRY_OPTOUT=1 /opt/dotnet/dotnet tool install dotnet-sonarscanner --tool-path /opt/dotnet-tools; \
    git config --system --add safe.directory '*'

# Cachés de dependencias dentro de JENKINS_HOME (volumen persistente): pip, npm, Maven (~/.m2),
# NuGet (~/.nuget) y Go viven en el home del usuario jenkins y sobreviven entre builds.
ENV PATH=/opt/node/bin:/opt/go/bin:/opt/maven/bin:/opt/sonar-scanner/bin:/opt/dotnet:/opt/dotnet-tools:$PATH \
    DOTNET_ROOT=/opt/dotnet \
    DOTNET_CLI_TELEMETRY_OPTOUT=1 \
    DOTNET_NOLOGO=1 \
    GOPATH=/var/jenkins_home/.cache/go \
    GOMODCACHE=/var/jenkins_home/.cache/go/pkg/mod \
    GOCACHE=/var/jenkins_home/.cache/go-build

# 4) Política CSP para que el HTML BDD publicado (estilos en línea) se vea bien
COPY init.groovy.d/ /usr/share/jenkins/ref/init.groovy.d/

# 5) Entrypoint: ajusta permisos del socket Docker del host y baja a usuario jenkins
COPY entrypoint.sh /usr/local/bin/entrypoint-reto7.sh
RUN chmod +x /usr/local/bin/entrypoint-reto7.sh
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint-reto7.sh"]
