FROM mcr.microsoft.com/dotnet/sdk:8.0 AS builder
WORKDIR /src
COPY Vacaciones.csproj .
RUN dotnet restore
COPY . .
RUN dotnet publish -c Release -o /app --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:8.0
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /app .
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
USER app
EXPOSE 8085
ENV ASPNETCORE_URLS=http://0.0.0.0:8085
# Carga los Docker Secrets (variables *_FILE) y luego ejecuta el servicio
ENTRYPOINT ["/bin/sh","/usr/local/bin/docker-entrypoint.sh","dotnet","Vacaciones.dll"]
