package co.edu.uq.notificaciones;

import io.swagger.v3.oas.annotations.Operation;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.actuate.health.HealthComponent;
import org.springframework.boot.actuate.health.HealthEndpoint;
import org.springframework.boot.actuate.health.Status;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Reto 8: /health con el formato común del ecosistema. Reutiliza los indicadores de Spring Boot
 * Actuator ("db" para PostgreSQL y "rabbit" para RabbitMQ). 200 si todo está UP, 503 si algo cae.
 */
@RestController
public class HealthController {
    private final HealthEndpoint health;
    private final String service;

    public HealthController(HealthEndpoint health, @Value("${spring.application.name}") String service) {
        this.health = health;
        this.service = service;
    }

    @Operation(summary = "Estado del servicio y de sus dependencias")
    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> health() {
        var checks = new LinkedHashMap<String, String>();
        checks.put("database", status("db"));
        checks.put("messageBroker", status("rabbit"));
        var up = checks.values().stream().allMatch("UP"::equals);
        var body = new LinkedHashMap<String, Object>();
        body.put("status", up ? "UP" : "DOWN");
        body.put("service", service);
        body.put("checks", checks);
        return ResponseEntity.status(up ? 200 : 503).body(body);
    }

    private String status(String component) {
        HealthComponent result = health.healthForPath(component);
        return result != null && Status.UP.equals(result.getStatus()) ? "UP" : "DOWN";
    }
}
