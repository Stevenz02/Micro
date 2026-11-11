# language: es
Característica: Disponibilidad del sistema

  Escenario: El Gateway responde a la consulta de salud
    Cuando consulto la salud del Gateway
    Entonces la respuesta debe tener código 200
    Y la respuesta indica que el Gateway está operativo
