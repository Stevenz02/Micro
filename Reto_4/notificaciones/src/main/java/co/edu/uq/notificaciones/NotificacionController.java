package co.edu.uq.notificaciones;

import io.swagger.v3.oas.annotations.Operation;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class NotificacionController {
    private final NotificacionRepository repository;
    public NotificacionController(NotificacionRepository repository) { this.repository = repository; }

    @Operation(summary = "Listar el historial completo")
    @GetMapping("/notificaciones")
    public List<Notificacion> all() { return repository.findAll(); }

    @Operation(summary = "Listar notificaciones de un empleado")
    @GetMapping("/notificaciones/{empleadoId}")
    public List<Notificacion> byEmpleado(@PathVariable String empleadoId) { return repository.findByEmpleado(empleadoId); }
}
