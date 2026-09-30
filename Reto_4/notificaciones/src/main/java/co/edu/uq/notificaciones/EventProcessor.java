package co.edu.uq.notificaciones;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.time.OffsetDateTime;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class EventProcessor {
    private static final Logger log = LoggerFactory.getLogger(EventProcessor.class);
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

    @Transactional
    public boolean process(byte[] body) throws IOException {
        var event = mapper.readTree(body);
        if (event == null || !event.isObject()) throw new IllegalArgumentException("Envelope no es objeto");
        var id = UUID.fromString(required(event, "id"));
        var type = required(event, "type");
        if (event.path("version").asInt(-1) != 1) throw new IllegalArgumentException("Version no soportada");
        if (!"empleados-service".equals(event.path("producer").asText())
            && !"vacaciones-service".equals(event.path("producer").asText()))
            throw new IllegalArgumentException("Productor no soportado");
        OffsetDateTime.parse(required(event, "occurredAt"));
        var data = event.path("data");
        if (!data.isObject()) throw new IllegalArgumentException("data no es objeto");
        var employeeId = required(data, "empleadoId");
        var email = required(data, "email");
        String notificationType;
        String message;
        switch (type) {
            case "empleado.creado" -> {
                if (!"empleados-service".equals(event.path("producer").asText()))
                    throw new IllegalArgumentException("Productor de alta invalido");
                required(data, "nombre"); required(data, "apellido"); required(data, "numeroEmpleado");
                required(data, "cargo"); required(data, "area"); required(data, "departamentoId");
                required(data, "fechaIngreso");
                if (!"ACTIVO".equals(required(data, "estado"))) throw new IllegalArgumentException("Estado invalido");
                notificationType = "ALTA";
                message = "Alta de empleado registrada";
            }
            case "empleado.retirado" -> {
                if (!"empleados-service".equals(event.path("producer").asText()))
                    throw new IllegalArgumentException("Productor de retiro invalido");
                OffsetDateTime.parse(required(data, "fechaRetiro"));
                var reason = required(data, "motivo");
                notificationType = "RETIRO";
                message = "Retiro de empleado registrado: " + reason;
            }
            case "vacaciones.programadas" -> {
                if (!"vacaciones-service".equals(event.path("producer").asText()))
                    throw new IllegalArgumentException("Productor de vacaciones invalido");
                required(data, "vacacionesId");
                var start = required(data, "fechaInicio");
                var end = required(data, "fechaFin");
                var days = data.path("diasHabiles").asInt(-1);
                if (days < 0) throw new IllegalArgumentException("diasHabiles invalido");
                notificationType = "VACACIONES";
                message = "Vacaciones programadas del " + start + " al " + end + " (" + days + " dias habiles)";
            }
            default -> throw new IllegalArgumentException("Tipo de evento no soportado: " + type);
        }
        var inserted = jdbc.update("INSERT INTO eventos_procesados(id) VALUES(?) ON CONFLICT DO NOTHING", id);
        if (inserted == 0) {
            log.info("evento_duplicado id={} type={}", id, type);
            return false;
        }
        jdbc.update("INSERT INTO notificaciones(id,tipo,destinatario,mensaje,empleado_id) VALUES(?,?,?,?,?)",
            id, notificationType, email, message, employeeId);
        log.info("evento_procesado id={} type={} empleadoId={}", id, type, employeeId);
        return true;
    }
}
