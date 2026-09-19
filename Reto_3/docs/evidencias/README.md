# Evidencias futuras

No hay capturas ficticias en esta fase. Cuando el integrante encargado complete
Docker, debe capturar:

1. Acceso directo a empleados rechazado desde el host.
2. Acceso directo a departamentos rechazado desde el host.
3. El mismo recurso funcionando via Gateway.
4. Primeras solicitudes lentas mientras el Circuit Breaker esta `closed`.
5. Respuesta 503 inmediata cuando el Circuit Breaker queda `open`.
6. Estado `open` observable en `/health/dependencies`.
7. Restauracion de `departamentos-service`.
8. Transicion de recuperacion tras el `reset_timeout`.
9. Estado `closed` tras una llamada exitosa.
10. Respuesta 400 para departamento inexistente luego de recuperarse.
