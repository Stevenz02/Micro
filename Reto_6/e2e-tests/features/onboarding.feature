# language: es
Característica: Alta y activación de empleados
  Como administrador
  Quiero registrar empleados y que reciban acceso al sistema

  Escenario: El registro produce cuenta y notificaciones sin transportar contraseñas
    Dado que actúo como "ADMIN"
    Cuando registro un empleado único
    Entonces la respuesta debe tener código 201
    Y eventualmente se registra la traza de alta del empleado
    Y eventualmente aparece el token de activación en una notificación de seguridad
    Y el empleado registrado tiene los datos solicitados

  Escenario: El empleado establece su contraseña y puede iniciar sesión
    Dado que existe un empleado registrado con token de activación
    Cuando establece su contraseña con el token
    Entonces la respuesta debe tener código 200
    Y eventualmente inicia sesión con la nueva contraseña
    Y eventualmente se notifica la activación inicial

  Escenario: Un token de activación solo se usa una vez
    Dado que existe un empleado registrado con token de activación
    Cuando establece su contraseña con el token
    Entonces la respuesta debe tener código 200
    Cuando intenta reutilizar el token de activación
    Entonces la respuesta debe tener código 400

  Escenario: Un departamento inexistente impide el registro
    Dado que actúo como "ADMIN"
    Cuando registro un empleado en un departamento inexistente
    Entonces la respuesta debe tener código 400

  Escenario: El registro exige todos los campos
    Dado que actúo como "ADMIN"
    Cuando registro un empleado sin apellido
    Entonces la respuesta debe tener código 422

  Esquema del escenario: La identidad del empleado debe ser única
    Dado que existe un empleado registrado
    Cuando registro otro empleado con el mismo "<campo>"
    Entonces la respuesta debe tener código 400

    Ejemplos:
      | campo          |
      | email          |
      | numeroEmpleado |
