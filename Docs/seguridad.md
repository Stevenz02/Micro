<!-- Pagina 1 de 18 -->

# Seguridad

Arquitectura Basada en Microservicios Área de infraestructura

Programa de Ingeniería de Sistemas y Computación Facultad de Ingeniería

---

<!-- Pagina 2 de 18 -->

Contenido

### Access token

- JWT

   - Qué es JWT

   - Estructura de JWT

   - Cifrados usados en JWT

   - Funcionamiento de JWT

   - Ventajas

   - Desventajas

---

<!-- Pagina 3 de 18 -->

Access token

---

<!-- Pagina 4 de 18 -->

## Access token

- Problema: ¿Cómo comunicar la identidad del cliente a los servicios que atienden una solicitud? Posible solución: Usar un Servidor de Autorización o (Identity Provider) para generar un identificador que permita a un cliente acceder a recursos protegidos sin compartir credenciales en cada solicitud. Autenticación: El usuario o cliente se autentica ante el Servidor de Autorización o Proveedor de Identidad.

   - Generación de Access Token: El Servidor de Autorización o Proveedor de Identidad verifica la identidad del usuario. Si la verificación es exitosa, el servidor emitirá un Access Token con información sobre el usuario y sus permisos. El token generado es firmado por el servidor.

   - Uso del Access Token: El cliente incluye el Access Token en cada solicitud realizada al Proveedor de Servicio o Recursos.

   - Validación: El Proveedor de Servicio o Recursos valida el Access Token usando las credenciales del servidor y, si es válido, concede acceso al recurso solicitado.

- NOTA: El Proveedor de Servicio o Recursos es responsable de propagar la identidad del usuario.

---

<!-- Pagina 5 de 18 -->

## Access token

### Beneficios

- Seguridad mejorada: Evita compartir credenciales en cada solicitud, reduciendo el riesgo de exposición.

- Escalabilidad: Compatible con arquitecturas sin estado (stateless), facilitando la distribución de carga en sistemas con múltiples instancias.

- Flexibilidad y granularidad: Se pueden definir permisos específicos mediante scopes en el token.

- Eficiencia: Los servicios pueden verificar localmente que el solicitante esté autorizado para realizar una operación sin necesidad de consultar una base de datos.

---

<!-- Pagina 6 de 18 -->

## Access token

- Dificultades

   - Riesgo de exposición: Si un Access Token es robado, un atacante puede usarlo hasta que expire.

   - Almacenamiento seguro: En aplicaciones web, guardar tokens en localStorage puede ser riesgoso ante ataques XSS.

   - Revocación compleja: Un Access Token no pueden revocarse fácilmente antes de su expiración.

   - Cada servicio se debe hacer responsable de la verificación y retransmisión del token.

---

<!-- Pagina 7 de 18 -->

## JWT

---

<!-- Pagina 8 de 18 -->

<!-- Start of picture text -->
¿Qué es JWT?<br><!-- End of picture text -->

JSON Web Token (JWT) es un estándar de autenticación y autorización. Es basado en Json

- Usa algoritmos de cifrado para garantizar la seguridad de la información transmitida. Desarrollado por el Grupo de Trabajo de JSON Web Token de la IETF (Internet Engineering Task Force) en 2010.

- Se definió como estándar en 2015 bajo el RFC 7519.

---

<!-- Pagina 9 de 18 -->

## Estructura de JWT


Información sobre el token en si mismo y el algoritmo de firma utilizado.

Información que se desea transmitir la cual puede incluir cualquier dato en formato JSON.

Cadena cifrada que permite verificar la autenticidad del token.

---

<!-- Pagina 10 de 18 -->

## Estructura de JWT: Header

Cada token tiene un header, que puede tener las siguientes propiedades: alg: Algoritmo principal utilizado para firmar y/o descifrar el JWT

typ: Tipo de token. Este parámetro sólo está pensado como ayuda para usos en los que los JWT puedan mezclarse con otros objetos que lleven una cabecera JOSE. Cuando está presente, esta demanda debe establecerse con el valor JWT.

cty: Tipo de contenido del token, es usado cuando el token contiene otro token, en ese caso se establece con el valor JWT.

---

<!-- Pagina 11 de 18 -->

## Estructura de JWT: Payload

Contiene los datos de interés o útiles en forma de cadena de texto o URI.

- iss: Identifica de forma única a la parte que emitió el JWT. Sensible al uso mayúsculas y minúsculas.

- sub: Identifica al sujeto del token, entidad de la cual el token contiene información. aud: Identifica de forma única a los destinatarios del token.

- exp: Establece el momento exacto a partir del cual este JWT se considera inválido. nbf: Establece el momento exacto a partir del cual este JWT se considera válido.

- iat: Fecha y hora en que se emitió el token.

- jti: Identificador único para este JWT.

---

<!-- Pagina 12 de 18 -->

## Cifrados usados en JWT

Ninguno (none): Cuando no se hace uso de un algoritmo de cifrado, este tipo de practica se considera en extremo insegura.

Simétrico: Se hace uso de una llave (secreto) compartido, el cual es usado para firmar el token y para verificarlo.

Asimétrico: Usa llaves publicas y privadas para firmar y verificar el token. Tipos: Según la especificación JWA (RFC 7518) pueden usarse el HS256, RS256, ES256, otros algoritmos soportados son (HS384, HS512, RS384, RS512, ES384, ES512, PS256, PS384, PS512)

---

<!-- Pagina 13 de 18 -->

<!-- Start of picture text -->
¿Cómo funciona?<br><!-- End of picture text -->

---

<!-- Pagina 14 de 18 -->

## Ventajas

- Seguridad: Proporciona una forma segura de transmitir información entre diferentes partes de una aplicación. Simplicidad: Es fácil de implementar y usar.

- Escalabilidad: No es necesario realizar múltiples solicitudes al servidor de autenticación para cada solicitud de recursos protegidos.

- Portabilidad: Es una tecnología independiente del lenguaje y del protocolo.

- Flexibilidad: Permite incluir información adicional en el token.

- Sin gestión de sesiones: Los tokens son autocontenidos.

- Portable: Un token puede usarse con múltiples backends.

- No requiere cookies: Facilita su uso en celulares.

- Rendimiento: Los tokens generados no requieren consultas a bases de datos para su verificación.

---

<!-- Pagina 15 de 18 -->

## Desventajas

- Capacidad de almacenamiento: Por ser cifrados pueden llegar a ser muy grandes limitando la capacidad de almacenamiento de los tokens en algunos sistemas.

- Seguridad: Una vez emitido un token JWT, no es posible invalidarlo o revocarlo.

- Fuerza bruta: Pueden ser vulnerables a ataques de fuerza bruta, especialmente si se utilizan algoritmos de cifrado débiles o si se comparten secretos en múltiples sistemas.

- Privacidad: Los tokens JWT no proporcionan privacidad en sí mismos, ya que cualquier persona que tenga acceso al token puede ver su contenido.

- Tiempo de expiración: Un tiempo de expiración inadecuado puede llevar a que los token permanezcan activos por períodos prolongados.

---

<!-- Pagina 16 de 18 -->

## Amenazas Comunes

Fuerza bruta contra claves secretas.

Manipulación de la carga útil.

Ataques de replay.

Secuestro de sesión.

---

<!-- Pagina 17 de 18 -->

<!-- Start of picture text -->
Mejores Practicas<br><!-- End of picture text -->

- Utilizar algoritmos criptográficos fuertes. Gestionar claves de forma segura.

- Validar rigurosamente los tokens.

- Limitar la vida útil de los tokens.

- Proteger contra ataques de replay.

---

<!-- Pagina 18 de 18 -->

Arquitectura Basada en Microservicios Programa de Ingeniería de Sistemas y Computación Universidad del Quindío


2025 Christian Andrés Candela Uribe
