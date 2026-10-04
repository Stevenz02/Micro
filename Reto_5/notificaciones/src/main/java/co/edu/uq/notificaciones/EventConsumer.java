package co.edu.uq.notificaciones;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.rabbitmq.client.Channel;
import java.io.IOException;
import java.time.format.DateTimeParseException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

@Component
public class EventConsumer {
    private static final Logger log = LoggerFactory.getLogger(EventConsumer.class);
    private final EventProcessor processor;

    public EventConsumer(EventProcessor processor) { this.processor = processor; }

    @RabbitListener(queues = "notificaciones.events")
    public void receive(Message message, Channel channel) throws IOException {
        var tag = message.getMessageProperties().getDeliveryTag();
        try {
            processor.process(message.getBody());
            channel.basicAck(tag, false);
        } catch (IllegalArgumentException | JsonProcessingException | DateTimeParseException exception) {
            log.error("evento_invalido tag={} error={}", tag, exception.getMessage());
            channel.basicReject(tag, false);
        } catch (Exception exception) {
            log.error("evento_no_procesado tag={}", tag, exception);
            channel.basicNack(tag, false, true);
        }
    }
}
