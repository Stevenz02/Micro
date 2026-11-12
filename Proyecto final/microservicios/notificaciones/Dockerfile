FROM maven:3.9.9-eclipse-temurin-21-alpine AS builder
WORKDIR /src
COPY pom.xml .
RUN mvn -q -DskipTests dependency:go-offline
COPY src ./src
# Las pruebas se ejecutan aparte con `mvn test`; el build de la imagen solo empaqueta
RUN mvn -q -DskipTests package

FROM eclipse-temurin:21-jre-alpine
RUN addgroup -S app && adduser -S -G app app
WORKDIR /app
COPY --from=builder /src/target/notificaciones-service-8.0.0.jar app.jar
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
# Plantillas por defecto; el Compose las monta como volumen para editarlas sin recompilar
COPY plantillas /app/plantillas
USER app
EXPOSE 8084
# Carga los Docker Secrets (variables *_FILE) y luego ejecuta el servicio
ENTRYPOINT ["/bin/sh","/usr/local/bin/docker-entrypoint.sh","java","-jar","app.jar"]
