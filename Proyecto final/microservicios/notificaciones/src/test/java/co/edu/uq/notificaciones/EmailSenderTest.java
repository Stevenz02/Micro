package co.edu.uq.notificaciones;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.ArgumentCaptor;
import org.springframework.mail.MailSendException;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;

class EmailSenderTest {
    @TempDir Path dir;

    @Test void rendersTheMostSpecificTemplateAndSendsIt() throws Exception {
        Files.writeString(dir.resolve("cuenta.desactivada.txt"), "Asunto: General\n\nGeneral");
        Files.writeString(dir.resolve("cuenta.desactivada.RETIRO.txt"),
            "Asunto: Cuenta de {{email}} desactivada\r\n\r\nMotivo: {{motivo}}. {{desconocido}}\r\n");
        var mail = mock(JavaMailSender.class);
        var sender = new EmailSender(mail, dir, "rrhh@test.local");

        assertTrue(sender.send(List.of("cuenta.desactivada.RETIRO", "cuenta.desactivada"), "ana@example.test",
            Map.of("email", "ana@example.test", "motivo", "RETIRO")));

        var captor = ArgumentCaptor.forClass(SimpleMailMessage.class);
        verify(mail).send(captor.capture());
        var message = captor.getValue();
        assertEquals("rrhh@test.local", message.getFrom());
        assertEquals("ana@example.test", message.getTo()[0]);
        assertEquals("Cuenta de ana@example.test desactivada", message.getSubject());
        assertEquals("Motivo: RETIRO. {{desconocido}}", message.getText());
    }

    @Test void eventWithoutTemplateSendsNothing() {
        var mail = mock(JavaMailSender.class);
        var sender = new EmailSender(mail, dir, "rrhh@test.local");
        assertFalse(sender.send(List.of("empleado.creado"), "ana@example.test", Map.of()));
        verify(mail, never()).send(any(SimpleMailMessage.class));
    }

    @Test void smtpFailureIsReportedButNeverThrown() throws Exception {
        Files.writeString(dir.resolve("usuario.creado.txt"), "Asunto: Bienvenida\n\nToken: {{token}}");
        var mail = mock(JavaMailSender.class);
        doThrow(new MailSendException("SMTP caído")).when(mail).send(any(SimpleMailMessage.class));
        var sender = new EmailSender(mail, dir, "rrhh@test.local");
        assertFalse(sender.send(List.of("usuario.creado"), "ana@example.test", Map.of("token", "abc")));
    }

    @Test void templateWithoutSubjectIsRejected() throws Exception {
        Files.writeString(dir.resolve("usuario.creado.txt"), "Hola sin asunto");
        var mail = mock(JavaMailSender.class);
        var sender = new EmailSender(mail, dir, "rrhh@test.local");
        assertFalse(sender.send(List.of("usuario.creado"), "ana@example.test", Map.of()));
        verify(mail, never()).send(any(SimpleMailMessage.class));
    }

    @Test void withoutSmtpServerNothingIsSent() {
        var sender = new EmailSender((JavaMailSender) null, dir, "rrhh@test.local");
        assertFalse(sender.send(List.of("usuario.creado"), "ana@example.test", Map.of()));
    }

    @Test void nullValuesRenderAsEmptyText() {
        var values = new java.util.HashMap<String, String>();
        values.put("a", null);
        assertEquals("[]", EmailSender.render("[{{a}}]", values));
    }
}
