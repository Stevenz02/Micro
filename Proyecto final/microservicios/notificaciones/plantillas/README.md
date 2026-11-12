# Plantillas de correo

Una plantilla por evento: `<tipo-de-evento>.txt` o, si el evento trae motivo,
`<tipo-de-evento>.<MOTIVO>.txt` (se usa la más específica que exista).

- La **primera línea** debe ser `Asunto: ...`; el resto es el cuerpo.
- Marcadores disponibles (según el evento): `{{email}}`, `{{empleadoId}}`, `{{token}}`,
  `{{expiraEn}}`, `{{fechaInicio}}`, `{{fechaFin}}`, `{{diasHabiles}}`, `{{motivo}}`,
  `{{fechaRetiro}}`, `{{nombre}}`, `{{apellido}}`, `{{cargo}}`, `{{area}}`, `{{mensaje}}`.
- Un evento **sin plantilla** no envía correo: solo queda en el historial de notificaciones.
- La carpeta se monta como volumen en `/app/plantillas`: los cambios aplican al siguiente
  correo, sin recompilar ni reiniciar el servicio.

Ninguna plantilla debe incluir contraseñas: el sistema no las genera ni las transmite.
