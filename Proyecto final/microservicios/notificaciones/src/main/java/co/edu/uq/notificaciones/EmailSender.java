package co.edu.uq.notificaciones;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Component;

/**
 * Envío de correo por SMTP con plantillas configurables.
 *
 * Cada plantilla es un archivo de texto en el directorio de plantillas (montado como volumen,
 * así se edita sin recompilar): la primera línea es "Asunto: ..." y el resto es el cuerpo.
 * Los marcadores {{nombre}} se sustituyen con los datos del evento. Un evento sin plantilla
 * no genera correo (solo queda registrado en el historial).
 */
@Component
public class EmailSender {
    private static final Logger log = LoggerFactory.getLogger(EmailSender.class);
    private static final String SUBJECT_PREFIX = "Asunto:";

    private final JavaMailSender mailSender;
    private final Path templatesDir;
    private final String from;

    @Autowired
    public EmailSender(ObjectProvider<JavaMailSender> mailSender,
            @Value("${notificaciones.plantillas.dir:/app/plantillas}") String templatesDir,
            @Value("${notificaciones.remitente:rrhh@empresa.local}") String from) {
        this(mailSender.getIfAvailable(), Path.of(templatesDir), from);
    }

    EmailSender(JavaMailSender mailSender, Path templatesDir, String from) {
        this.mailSender = mailSender;
        this.templatesDir = templatesDir;
        this.from = from;
    }

    static String render(String template, Map<String, String> values) {
        var result = template;
        for (var entry : values.entrySet()) {
            var value = entry.getValue() == null ? "" : entry.getValue();
            result = result.replace("{{" + entry.getKey() + "}}", value);
        }
        return result;
    }

    /**
     * Envía el correo con la primera plantilla existente de la lista (de más específica a más general).
     * Nunca lanza: un fallo de SMTP no debe impedir que el evento quede procesado.
     *
     * @return true si el correo se entregó al servidor SMTP
     */
    public boolean send(List<String> templateNames, String to, Map<String, String> values) {
        if (mailSender == null) return false;
        try {
            Path file = null;
            for (var name : templateNames) {
                var candidate = templatesDir.resolve(name + ".txt");
                if (Files.isRegularFile(candidate)) {
                    file = candidate;
                    break;
                }
            }
            if (file == null) return false;
            var text = render(Files.readString(file, StandardCharsets.UTF_8), values).replace("\r\n", "\n");
            var lineEnd = text.indexOf('\n');
            var subjectLine = lineEnd < 0 ? text : text.substring(0, lineEnd);
            if (!subjectLine.startsWith(SUBJECT_PREFIX)) {
                throw new IOException("La plantilla " + file.getFileName() + " debe empezar con 'Asunto:'");
            }
            var message = new SimpleMailMessage();
            message.setFrom(from);
            message.setTo(to);
            message.setSubject(subjectLine.substring(SUBJECT_PREFIX.length()).trim());
            message.setText(lineEnd < 0 ? "" : text.substring(lineEnd + 1).strip());
            mailSender.send(message);
            log.info("correo_enviado plantilla={} destinatario={}", file.getFileName(), to);
            return true;
        } catch (Exception exception) {
            log.warn("correo_no_enviado destinatario={} error={}", to, exception.getMessage());
            return false;
        }
    }
}
