package co.edu.uq.notificaciones;

import jakarta.annotation.PostConstruct;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

@Component
public class SchemaMigration {
    private final JdbcTemplate jdbc;
    public SchemaMigration(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    @PostConstruct
    public void migrate() {
        jdbc.execute("ALTER TABLE notificaciones DROP CONSTRAINT IF EXISTS notificaciones_tipo_check");
        jdbc.execute("ALTER TABLE notificaciones ADD CONSTRAINT notificaciones_tipo_check "
            + "CHECK (tipo IN ('ALTA','RETIRO','BIENVENIDA','DESVINCULACION','VACACIONES'))");
    }
}
