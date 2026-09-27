FROM maven:3.9.9-eclipse-temurin-21-alpine AS builder
WORKDIR /src
COPY pom.xml .
RUN mvn -q -DskipTests dependency:go-offline
COPY src ./src
RUN mvn -q package

FROM eclipse-temurin:21-jre-alpine
RUN addgroup -S app && adduser -S -G app app
WORKDIR /app
COPY --from=builder /src/target/notificaciones-service-4.0.0.jar app.jar
USER app
EXPOSE 8084
ENTRYPOINT ["java","-jar","app.jar"]
