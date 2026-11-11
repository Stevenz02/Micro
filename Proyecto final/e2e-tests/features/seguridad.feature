# language: es
Característica: Seguridad y control de acceso
  Como usuario del sistema
  Quiero que mis permisos se respeten en todas las rutas

  Escenario: Consultar empleados sin token
    Cuando consulto empleados sin token
    Entonces la respuesta debe tener código 401

  Escenario: Consultar empleados con un token malformado
    Cuando consulto empleados con un token malformado
    Entonces la respuesta debe tener código 401

  Escenario: Consultar empleados con la firma alterada
    Dado que actúo como "ADMIN"
    Cuando consulto empleados con la firma alterada
    Entonces la respuesta debe tener código 401

  Escenario: Un usuario puede leer pero no crear ni retirar empleados
    Dado que existe un empleado activo con credenciales establecidas
    Y que actúo como "USER"
    Cuando consulto empleados
    Entonces la respuesta debe tener código 200
    Cuando intento crear otro empleado
    Entonces la respuesta debe tener código 403
    Cuando intento retirar mi empleado
    Entonces la respuesta debe tener código 403

  Escenario: Un usuario puede actualizar su perfil pero no uno ajeno
    Dado que existe un empleado activo con credenciales establecidas
    Y que actúo como "USER"
    Cuando actualizo mi perfil
    Entonces la respuesta debe tener código 200
    Cuando intento actualizar otro perfil
    Entonces la respuesta debe tener código 403

  Escenario: Los headers de identidad falsificados no elevan privilegios
    Dado que existe un empleado activo con credenciales establecidas
    Y que actúo como "USER"
    Cuando consulto el token de seguridad falsificando el rol ADMIN
    Entonces la respuesta debe tener código 403

  Escenario: Un token de activación no sirve para consultar empleados
    Dado que existe un empleado registrado con token de activación
    Cuando consulto empleados con el token de activación
    Entonces la respuesta debe tener código 401

  Escenario: El administrador puede crear, actualizar y retirar empleados
    Dado que actúo como "ADMIN"
    Y que existe un empleado registrado
    Cuando actualizo el cargo del empleado
    Entonces la respuesta debe tener código 200
    Cuando retiro el empleado
    Entonces la respuesta debe tener código 200
    Y el empleado queda conservado con estado RETIRADO

  Escenario: El administrador puede consultar el token simulado
    Dado que existe un empleado registrado con token de activación
    Y que actúo como "ADMIN"
    Cuando consulto el token simulado de seguridad
    Entonces la respuesta debe tener código 200
    Y la respuesta contiene el token de activación
