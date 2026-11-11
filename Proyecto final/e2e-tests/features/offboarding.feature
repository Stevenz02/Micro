# language: es
Característica: Retiro lógico y desactivación definitiva
  Como administrador
  Quiero conservar el historial del empleado retirado y bloquear su acceso

  Escenario: El retiro conserva al empleado y bloquea la cuenta
    Dado que existe un empleado activo con credenciales establecidas
    Cuando retiro el empleado
    Entonces la respuesta debe tener código 200
    Y el empleado queda conservado con estado RETIRADO
    Y aparece en la consulta de auditoría
    Y eventualmente se registra la traza de retiro
    Y eventualmente se notifica la desactivación permanente
    Y el empleado no puede iniciar sesión
    Cuando solicita recuperar su contraseña después del retiro
    Entonces recibe la respuesta genérica de recuperación
    Y no se genera un nuevo token de recuperación

  Escenario: El fin de vacaciones no reactiva una cuenta retirada
    Dado que existe un empleado activo con credenciales establecidas
    Cuando programo vacaciones para hoy
    Entonces la respuesta debe tener código 201
    Y eventualmente se notifica la suspensión por vacaciones
    Cuando retiro el empleado
    Entonces la respuesta debe tener código 200
    Y eventualmente se notifica la desactivación permanente
    Y eventualmente se notifica el fin de vacaciones
    Y el empleado no puede iniciar sesión
