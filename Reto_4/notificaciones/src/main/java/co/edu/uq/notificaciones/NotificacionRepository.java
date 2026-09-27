package co.edu.uq.notificaciones;

import java.util.List;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class NotificacionRepository {
    private final JdbcTemplate jdbc;
    public NotificacionRepository(JdbcTemplate jdbc) { this.jdbc = jdbc; }
    private static final String SELECT = "SELECT id,tipo,destinatario,mensaje,fecha_envio,empleado_id FROM notificaciones";
    private static Notificacion map(java.sql.ResultSet rs, int row) throws java.sql.SQLException {
        return new Notificacion(rs.getObject("id", java.util.UUID.class), rs.getString("tipo"),
            rs.getString("destinatario"), rs.getString("mensaje"),
            rs.getObject("fecha_envio", java.time.OffsetDateTime.class), rs.getString("empleado_id"));
    }
    public List<Notificacion> findAll() { return jdbc.query(SELECT + " ORDER BY fecha_envio,id", NotificacionRepository::map); }
    public List<Notificacion> findByEmpleado(String id) { return jdbc.query(SELECT + " WHERE empleado_id=? ORDER BY fecha_envio,id", NotificacionRepository::map, id); }
}
