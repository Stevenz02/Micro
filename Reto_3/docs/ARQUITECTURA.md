# Arquitectura Reto 3

```mermaid
flowchart LR
    Cliente --> Gateway[API Gateway FastAPI]
    Gateway --> Empleados[empleados-service FastAPI]
    Gateway --> Departamentos[departamentos-service Express]
    Empleados --> DbEmp[(PostgreSQL empleados)]
    Departamentos --> DbDep[(PostgreSQL departamentos)]
    Empleados -->|HTTP REST + timeout + retry + Circuit Breaker| Departamentos
```

Cuando se dockerice, el cliente debe acceder solo al Gateway. Empleados y
departamentos quedaran accesibles dentro de la red de Compose mediante `expose`,
sin `ports` publicados al host.
