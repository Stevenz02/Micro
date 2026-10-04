package co.edu.uq.notificaciones;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
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

    public EventProcessor(JdbcTemplate jdbc, ObjectMapper mapper) {
        this.jdbc = jdbc;
        this.mapper = mapper;
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

        switch (type) {
            case "empleado.creado" -> {
                employeeId = required(data, "empleadoId");
                required(data, "nombre"); required(data, "apellido"); required(data, "numeroEmpleado");
                required(data, "cargo"); required(data, "area"); required(data, "departamentoId");
                LocalDate.parse(required(data, "fechaIngreso"));
                if (!"ACTIVO".equals(required(data, "estado"))) throw new IllegalArgumentException("Estado inválido");
                notificationType = "ALTA";
                message = "Alta de empleado registrada";
            }
            case "empleado.retirado" -> {
                employeeId = required(data, "empleadoId");
                utc(required(data, "fechaRetiro"));
                var reason = required(data, "motivo");
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
                notificationType = "VACACIONES";
                message = "Vacaciones programadas del " + start + " al " + end + " (" + days + " días hábiles)";
            }
            case "vacaciones.iniciadas" -> {
                employeeId = required(data, "empleadoId");
                required(data, "vacacionesId");
                var start = LocalDate.parse(required(data, "fechaInicio"));
                var end = LocalDate.parse(required(data, "fechaFin"));
                notificationType = "VACACIONES";
                message = "Vacaciones iniciadas del " + start + " al " + end;
            }
            case "vacaciones.finalizadas" -> {
                employeeId = required(data, "empleadoId");
                required(data, "vacacionesId");
                var end = LocalDate.parse(required(data, "fechaFin"));
                notificationType = "VACACIONES";
                message = "Vacaciones finalizadas el " + end;
            }
            case "usuario.creado" -> {
                employeeId = required(data, "empleadoId");
                deliveryToken = required(data, "tokenActivacion");
                expiresAt = utc(required(data, "expiraEn"));
                notificationType = "SEGURIDAD";
                message = "Cuenta creada: establezca su contraseña con el token de activación";
            }
            case "usuario.recuperacion" -> {
                deliveryToken = required(data, "tokenRecuperacion");
                expiresAt = utc(required(data, "expiraEn"));
                notificationType = "SEGURIDAD";
                message = "Recuperación solicitada: restablezca su contraseña con el token de recuperación";
            }
            case "cuenta.activada" -> {
                employeeId = required(data, "empleadoId");
                var reason = required(data, "motivo");
                if (!reason.equals("ACTIVACION_INICIAL") && !reason.equals("FIN_VACACIONES"))
                    throw new IllegalArgumentException("Motivo de activación inválido");
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
                notificationType = "CUENTA";
                message = "Cuenta desactivada: " + reason;
            }
            default -> throw new IllegalArgumentException("Tipo de evento no soportado");
        }

        var inserted = jdbc.update("INSERT INTO eventos_procesados(id) VALUES(?) ON CONFLICT DO NOTHING", id);
        if (inserted == 0) {
            log.info("evento_duplicado id={} type={}", id, type);
            return false;
        }
        jdbc.update("INSERT INTO notificaciones(id,tipo,destinatario,mensaje,empleado_id,token_entrega,token_expira_en) "
                + "VALUES(?,?,?,?,?,?,?)", id, notificationType, email, message, employeeId, deliveryToken, expiresAt);
        log.info("evento_procesado id={} type={}", id, type);
        return true;
    }
}
