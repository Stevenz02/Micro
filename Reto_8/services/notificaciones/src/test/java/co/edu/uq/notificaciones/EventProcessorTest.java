package co.edu.uq.notificaciones;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.startsWith;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;

class EventProcessorTest {
    private JdbcTemplate jdbc;
    private EventProcessor processor;
    private final ObjectMapper mapper = new ObjectMapper();

    @BeforeEach void setup() {
        jdbc = org.mockito.Mockito.mock(JdbcTemplate.class);
        processor = new EventProcessor(jdbc, mapper);
    }

    private byte[] event(UUID id, String type, String producer, Map<String, Object> data) throws Exception {
        return mapper.writeValueAsBytes(Map.of(
            "id", id.toString(), "type", type, "version", 1,
            "occurredAt", "2026-10-04T12:00:00Z", "producer", producer, "data", data));
    }

    @Test void onboardingStoresTokenOutsidePublicMessage() throws Exception {
        var id = UUID.randomUUID();
        when(jdbc.update(startsWith("INSERT INTO eventos_procesados"), eq(id))).thenReturn(1);
        assertTrue(processor.process(event(id, "usuario.creado", "auth-service", Map.of(
            "empleadoId", "E001", "email", "ana@example.test", "tokenActivacion", "token-de-prueba",
            "expiraEn", "2026-10-04T12:30:00Z"))));
        verify(jdbc).update(startsWith("INSERT INTO notificaciones"), eq(id), eq("SEGURIDAD"),
            eq("ana@example.test"), eq("Cuenta creada: establezca su contraseña con el token de activación"),
            eq("E001"), eq("token-de-prueba"), any());
    }

    @Test void recoveryHasNoInventedEmployeeId() throws Exception {
        var id = UUID.randomUUID();
        when(jdbc.update(startsWith("INSERT INTO eventos_procesados"), eq(id))).thenReturn(1);
        assertTrue(processor.process(event(id, "usuario.recuperacion", "auth-service", Map.of(
            "email", "ana@example.test", "tokenRecuperacion", "token-de-prueba",
            "expiraEn", "2026-10-04T12:30:00Z"))));
        verify(jdbc).update(startsWith("INSERT INTO notificaciones"), eq(id), eq("SEGURIDAD"),
            eq("ana@example.test"), eq("Recuperación solicitada: restablezca su contraseña con el token de recuperación"),
            eq(null), eq("token-de-prueba"), any());
    }

    @Test void accountAndVacationEventsCreateOnlyOneRecordEach() throws Exception {
        var id = UUID.randomUUID();
        when(jdbc.update(startsWith("INSERT INTO eventos_procesados"), eq(id))).thenReturn(1);
        assertTrue(processor.process(event(id, "cuenta.desactivada", "auth-service", Map.of(
            "empleadoId", "E001", "email", "ana@example.test", "motivo", "VACACIONES", "permanente", false))));
        verify(jdbc).update(startsWith("INSERT INTO notificaciones"), eq(id), eq("CUENTA"),
            eq("ana@example.test"), eq("Cuenta desactivada: VACACIONES"), eq("E001"), eq(null), eq(null));
    }

    @Test void duplicateEventDoesNotInsertNotification() throws Exception {
        var id = UUID.randomUUID();
        when(jdbc.update(startsWith("INSERT INTO eventos_procesados"), eq(id))).thenReturn(0);
        assertFalse(processor.process(event(id, "cuenta.activada", "auth-service", Map.of(
            "empleadoId", "E001", "email", "ana@example.test", "motivo", "FIN_VACACIONES"))));
        verify(jdbc, never()).update(startsWith("INSERT INTO notificaciones"), any(), any(), any(), any(), any(), any(), any());
    }

    @Test void vacationTransitionsAndReactivationHaveExpectedMessages() throws Exception {
        var startId = UUID.randomUUID();
        var finishId = UUID.randomUUID();
        var accountId = UUID.randomUUID();
        when(jdbc.update(startsWith("INSERT INTO eventos_procesados"), any(UUID.class))).thenReturn(1);
        assertTrue(processor.process(event(startId, "vacaciones.iniciadas", "vacaciones-service", Map.of(
            "vacacionesId", "V001", "empleadoId", "E001", "email", "ana@example.test",
            "fechaInicio", "2026-10-04", "fechaFin", "2026-10-05"))));
        assertTrue(processor.process(event(finishId, "vacaciones.finalizadas", "vacaciones-service", Map.of(
            "vacacionesId", "V001", "empleadoId", "E001", "email", "ana@example.test",
            "fechaFin", "2026-10-05"))));
        assertTrue(processor.process(event(accountId, "cuenta.activada", "auth-service", Map.of(
            "empleadoId", "E001", "email", "ana@example.test", "motivo", "FIN_VACACIONES"))));
        verify(jdbc).update(startsWith("INSERT INTO notificaciones"), eq(startId), eq("VACACIONES"),
            eq("ana@example.test"), eq("Vacaciones iniciadas del 2026-10-04 al 2026-10-05"),
            eq("E001"), eq(null), eq(null));
        verify(jdbc).update(startsWith("INSERT INTO notificaciones"), eq(finishId), eq("VACACIONES"),
            eq("ana@example.test"), eq("Vacaciones finalizadas el 2026-10-05"),
            eq("E001"), eq(null), eq(null));
        verify(jdbc).update(startsWith("INSERT INTO notificaciones"), eq(accountId), eq("CUENTA"),
            eq("ana@example.test"), eq("Cuenta activada: FIN_VACACIONES"),
            eq("E001"), eq(null), eq(null));
    }
}
