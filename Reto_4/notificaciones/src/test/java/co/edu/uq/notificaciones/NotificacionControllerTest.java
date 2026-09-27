package co.edu.uq.notificaciones;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(NotificacionController.class)
class NotificacionControllerTest {
    @Autowired MockMvc mvc;
    @MockBean NotificacionRepository repository;

    @Test void listsHistory() throws Exception {
        when(repository.findAll()).thenReturn(List.of());
        mvc.perform(get("/notificaciones")).andExpect(status().isOk());
    }

    @Test void filtersByEmployee() throws Exception {
        when(repository.findByEmpleado("E001")).thenReturn(List.of());
        mvc.perform(get("/notificaciones/E001")).andExpect(status().isOk());
    }
}
