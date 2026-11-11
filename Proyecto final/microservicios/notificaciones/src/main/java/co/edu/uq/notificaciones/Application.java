package co.edu.uq.notificaciones;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.security.SecurityScheme;
import io.swagger.v3.oas.models.servers.Server;
import io.micrometer.observation.ObservationPredicate;
import java.util.List;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.http.server.observation.ServerRequestObservationContext;

@SpringBootApplication
public class Application {
    public static void main(String[] args) { SpringApplication.run(Application.class, args); }

    @Bean
    OpenAPI openApi() { return new OpenAPI().servers(List.of(new Server().url("/")))
        .components(new Components().addSecuritySchemes("BearerAuth",
            new SecurityScheme().type(SecurityScheme.Type.HTTP).scheme("bearer").bearerFormat("JWT"))); }

    /** Reto 8: las sondas (/health cada 5 s y /actuator/prometheus cada 15 s) no generan trazas ni métricas. */
    @Bean
    ObservationPredicate ignoreProbes() {
        return (name, context) -> !(context instanceof ServerRequestObservationContext server
            && (server.getCarrier().getRequestURI().equals("/health")
                || server.getCarrier().getRequestURI().startsWith("/actuator")));
    }
}
