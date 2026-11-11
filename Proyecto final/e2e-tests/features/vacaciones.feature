# language: es
Característica: Programación y ciclo de vacaciones
  Como administrador
  Quiero programar períodos válidos y suspender el acceso durante ellos

  Escenario: Un período válido genera confirmación
    Dado que existe un empleado activo con credenciales establecidas
    Cuando programo vacaciones futuras
    Entonces la respuesta debe tener código 201
    Y eventualmente se notifica la programación de vacaciones

  Escenario: La fecha final anterior al inicio se rechaza
    Dado que existe un empleado activo con credenciales establecidas
    Cuando programo vacaciones con fecha final anterior al inicio
    Entonces la respuesta debe tener código 400

  Escenario: Las vacaciones no pueden comenzar en el pasado
    Dado que existe un empleado activo con credenciales establecidas
    Cuando programo vacaciones en el pasado
    Entonces la respuesta debe tener código 400

  Escenario: El mismo día de inicio y fin es válido
    Dado que existe un empleado activo con credenciales establecidas
    Cuando programo vacaciones para hoy
    Entonces la respuesta debe tener código 201

  Escenario: No se pueden programar períodos superpuestos
    Dado que existe un empleado activo con credenciales establecidas
    Y que tiene vacaciones futuras programadas
    Cuando programo vacaciones que se solapan
    Entonces la respuesta debe tener código 400
    Y no aparece un período adicional para el empleado

  Escenario: El inicio suspende el login y el fin lo restablece
    Dado que existe un empleado activo con credenciales establecidas
    Cuando programo vacaciones para hoy
    Entonces la respuesta debe tener código 201
    Y eventualmente se notifica la suspensión por vacaciones
    Y el empleado no puede iniciar sesión
    Y eventualmente se notifica el fin de vacaciones
    Y eventualmente el empleado vuelve a iniciar sesión
