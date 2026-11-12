package co.edu.uq.notificaciones;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.micrometer.core.instrument.MeterRegistry;
import java.io.IOException;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class EventProcessor {
    private static final Logger log = LoggerFactory.getLogger(EventProcessor.class);
    private static final Map<String, String> PRODUCERS = Map.ofEntries(
        Map.entry("empleado.creado", "empleados-service"),
        Map.entry("empleado.retirado", "empleados-service"),
        Map.entry("vacaciones.programadas", "vacaciones-service"),
        Map.entry("vacaciones.iniciadas", "vacaciones-service"),
        Map.entry("vacaciones.finalizadas", "vacaciones-service"),
        Map.entry("usuario.creado", "auth-service"),
        Map.entry("usuario.recuperacion", "auth-service"),
        Map.entry("cuenta.activada", "auth-service"),
        Map.entry("cuenta.desactivada", "auth-service")
    );

    private final JdbcTemplate jdbc;
    private final ObjectMapper mapper;
    private final EmailSender emailSender;
    private final MeterRegistry meters;

    /** Sin correo ni métricas: lo usan las pruebas unitarias de las reglas de negocio. */
    public EventProcessor(JdbcTemplate jdbc, ObjectMapper mapper) {
        this(jdbc, mapper, null, null);
    }

    @Autowired
    public EventProcessor(JdbcTemplate jdbc, ObjectMapper mapper, EmailSender emailSender, MeterRegistry meters) {
        this.jdbc = jdbc;
        this.mapper = mapper;
        this.emailSender = emailSender;
        this.meters = meters;
    }

    private static String required(JsonNode node, String field) {
        var value = node.path(field).asText("").trim();
        if (value.isEmpty()) throw new IllegalArgumentException("Falta campo " + field);
        return value;
    }

    private static OffsetDateTime utc(String value) {
        var date = OffsetDateTime.parse(value);
        if (!date.getOffset().equals(ZoneOffset.UTC)) throw new IllegalArgumentException("Fecha no UTC");
        return date;
    }

    @Transactional
    public boolean process(byte[] body) throws IOException {
        var event = mapper.readTree(body);
        if (event == null || !event.isObject()) throw new IllegalArgumentException("Envelope no es objeto");
        var id = UUID.fromString(required(event, "id"));
        var type = required(event, "type");
        if (event.path("version").asInt(-1) != 1) throw new IllegalArgumentException("Versión no soportada");
        if (!PRODUCERS.containsKey(type) || !PRODUCERS.get(type).equals(required(event, "producer")))
            throw new IllegalArgumentException("Tipo o productor no soportado");
        utc(required(event, "occurredAt"));
        var data = event.path("data");
        if (!data.isObject()) throw new IllegalArgumentException("data no es objeto");

        String employeeId = null;
        String email = required(data, "email");
        String notificationType;
        String message;
        String deliveryToken = null;
        OffsetDateTime expiresAt = null;
        String templateVariant = null; // p. ej. cuenta.desactivada.RETIRO antes que cuenta.desactivada
        // Datos disponibles para los marcadores {{...}} de las plantillas de correo
        var values = new HashMap<String, String>();
        values.put("email", email);

        switch (type) {
            case "empleado.creado" -> {
                employeeId = required(data, "empleadoId");
                values.put("nombre", required(data, "nombre"));
                values.put("apellido", required(data, "apellido"));
                required(data, "numeroEmpleado");
                values.put("cargo", required(data, "cargo"));
                values.put("area", required(data, "area"));
                required(data, "departamentoId");
                LocalDate.parse(required(data, "fechaIngreso"));
                if (!"ACTIVO".equals(required(data, "estado"))) throw new IllegalArgumentException("Estado inválido");
                notificationType = "ALTA";
                message = "Alta de empleado registrada";
            }
            case "empleado.retirado" -> {
                employeeId = required(data, "empleadoId");
                values.put("fechaRetiro", utc(required(data, "fechaRetiro")).toString());
                var reason = required(data, "motivo");
                values.put("motivo", reason);
                notificationType = "RETIRO";
                message = "Retiro de empleado registrado: " + reason;
            }
            case "vacaciones.programadas" -> {
                employeeId = required(data, "empleadoId");
                required(data, "vacacionesId");
                var start = LocalDate.parse(required(data, "fechaInicio"));
                var end = LocalDate.parse(required(data, "fechaFin"));
                var days = data.path("diasHabiles").asInt(-1);
                if (days < 0) throw new IllegalArgumentException("diasHabiles inválido");
                values.put("fechaInicio", start.toString());
                values.put("fechaFin", end.toString());
                values.put("diasHabiles", String.valueOf(days));
                notificationType = "VACACIONES";
                message = "Vacaciones programadas del " + start + " al " + end + " (" + days + " días hábiles)";
            }
            case "vacaciones.iniciadas" -> {
                employeeId = required(data, "empleadoId");
                required(data, "vacacionesId");
                var start = LocalDate.parse(required(data, "fechaInicio"));
                var end = LocalDate.parse(required(data, "fechaFin"));
                values.put("fechaInicio", start.toString());
                values.put("fechaFin", end.toString());
                notificationType = "VACACIONES";
                message = "Vacaciones iniciadas del " + start + " al " + end;
            }
            case "vacaciones.finalizadas" -> {
                employeeId = required(data, "empleadoId");
                required(data, "vacacionesId");
                var end = LocalDate.parse(required(data, "fechaFin"));
                values.put("fechaFin", end.toString());
                notificationType = "VACACIONES";
                message = "Vacaciones finalizadas el " + end;
            }
            case "usuario.creado" -> {
                employeeId = required(data, "empleadoId");
                deliveryToken = required(data, "tokenActivacion");
                expiresAt = utc(required(data, "expiraEn"));
                values.put("token", deliveryToken);
                values.put("expiraEn", expiresAt.toString());
                notificationType = "SEGURIDAD";
                message = "Cuenta creada: establezca su contraseña con el token de activación";
            }
            case "usuario.recuperacion" -> {
                deliveryToken = required(data, "tokenRecuperacion");
                expiresAt = utc(required(data, "expiraEn"));
                values.put("token", deliveryToken);
                values.put("expiraEn", expiresAt.toString());
                notificationType = "SEGURIDAD";
                message = "Recuperación solicitada: restablezca su contraseña con el token de recuperación";
            }
            case "cuenta.activada" -> {
                employeeId = required(data, "empleadoId");
                var reason = required(data, "motivo");
                if (!reason.equals("ACTIVACION_INICIAL") && !reason.equals("FIN_VACACIONES"))
                    throw new IllegalArgumentException("Motivo de activación inválido");
                values.put("motivo", reason);
                templateVariant = reason;
                notificationType = "CUENTA";
                message = "Cuenta activada: " + reason;
            }
            case "cuenta.desactivada" -> {
                employeeId = required(data, "empleadoId");
                var reason = required(data, "motivo");
                var permanent = data.path("permanente");
                if (!permanent.isBoolean() || (reason.equals("RETIRO") != permanent.asBoolean())
                    || (!reason.equals("RETIRO") && !reason.equals("VACACIONES")))
                    throw new IllegalArgumentException("Motivo o permanencia inválidos");
                values.put("motivo", reason);
                templateVariant = reason;
                notificationType = "CUENTA";
                message = "Cuenta desactivada: " + reason;
            }
            default -> throw new IllegalArgumentException("Tipo de evento no soportado");
        }
        if (employeeId != null) values.put("empleadoId", employeeId);
        values.put("mensaje", message);

        // Deduplicación por el id del envelope: una reentrega no crea otra notificación ni otro correo
        var inserted = jdbc.update("INSERT INTO eventos_procesados(id) VALUES(?) ON CONFLICT DO NOTHING", id);
        if (inserted == 0) {
            log.info("evento_duplicado id={} type={}", id, type);
            return false;
        }
        jdbc.update("INSERT INTO notificaciones(id,tipo,destinatario,mensaje,empleado_id,token_entrega,token_expira_en) "
                + "VALUES(?,?,?,?,?,?,?)", id, notificationType, email, message, employeeId, deliveryToken, expiresAt);
        log.info("evento_procesado id={} type={}", id, type);

        // Correo real por SMTP. El token de activación/recuperación viaja solo dentro del correo:
        // nunca se escribe en los logs, y el sistema jamás genera ni transmite contraseñas.
        var sent = false;
        if (emailSender != null) {
            var templates = templateVariant == null ? List.of(type) : List.of(type + "." + templateVariant, type);
            sent = emailSender.send(templates, email, values);
        }
        if (meters != null) {
            meters.counter("notificaciones.enviadas", "tipo", notificationType, "evento", type,
                "correo", sent ? "enviado" : "solo_registro").increment();
        }
        log.info("[NOTIFICACIÓN] Tipo: {} | Para: {} | Correo: {} | Mensaje: \"{}\"", notificationType, email,
            sent ? "enviado" : "solo registro", message);
        return true;
    }
}
