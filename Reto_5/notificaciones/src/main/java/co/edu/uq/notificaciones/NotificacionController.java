package co.edu.uq.notificaciones;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

@RestController
@SecurityRequirement(name = "BearerAuth")
public class NotificacionController {
    private final NotificacionRepository repository;
    public NotificacionController(NotificacionRepository repository) { this.repository = repository; }

    @Operation(summary = "Listar el historial completo")
    @GetMapping("/notificaciones")
    public List<Notificacion> all() { return repository.findAll(); }

    @Operation(summary = "Listar notificaciones de un empleado")
    @GetMapping("/notificaciones/{empleadoId}")
    public List<Notificacion> byEmpleado(@PathVariable String empleadoId) { return repository.findByEmpleado(empleadoId); }

    @Operation(summary = "Consultar token de entrega simulado (solo ADMIN, mientras esté vigente)")
    @GetMapping("/notificaciones/seguridad/{id}/token")
    public Map<String, String> deliveryToken(@PathVariable UUID id,
            @RequestHeader(name = "X-Authenticated-Role", required = false) String role) {
        if (!"ADMIN".equals(role)) throw new ResponseStatusException(HttpStatus.FORBIDDEN);
        var token = repository.activeDeliveryToken(id);
        if (token == null) throw new ResponseStatusException(HttpStatus.NOT_FOUND);
        return Map.of("token", token);
    }
}
