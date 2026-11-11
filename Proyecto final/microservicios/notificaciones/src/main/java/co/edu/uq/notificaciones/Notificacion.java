package co.edu.uq.notificaciones;

import java.time.OffsetDateTime;
import java.util.UUID;

public record Notificacion(UUID id, String tipo, String destinatario, String mensaje,
                           OffsetDateTime fechaEnvio, String empleadoId) {}
