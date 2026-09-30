using System.Text.Json;
using Npgsql;
using RabbitMQ.Client.Events;

public sealed record EmployeeEvent(Guid Id, string Type, int Version, string OccurredAt, string Producer, JsonElement Data);

public sealed class EmployeeEventsConsumer(VacacionesRepository repository, ILogger<EmployeeEventsConsumer> logger) : BackgroundService {
    protected override async Task ExecuteAsync(CancellationToken stoppingToken) {
        while (!stoppingToken.IsCancellationRequested) {
            try {
                using var connection = RabbitPublisher.Factory().CreateConnection();
                using var channel = connection.CreateModel();
                channel.BasicQos(0, 1, false);
                var consumer = new AsyncEventingBasicConsumer(channel);
                consumer.Received += async (_, delivery) => {
                    try {
                        var eventData = JsonSerializer.Deserialize<EmployeeEvent>(delivery.Body.Span, new JsonSerializerOptions(JsonSerializerDefaults.Web))
                            ?? throw new JsonException("Envelope nulo");
                        var processed = await repository.ApplyEmployeeEvent(eventData);
                        if (processed) logger.LogInformation("evento_procesado id={Id} tipo={Type}", eventData.Id, eventData.Type);
                        else logger.LogInformation("evento_duplicado id={Id} tipo={Type}", eventData.Id, eventData.Type);
                        channel.BasicAck(delivery.DeliveryTag, false);
                    } catch (Exception exception) when (exception is JsonException or ArgumentException or FormatException) {
                        logger.LogError(exception, "Evento de empleado invalido; deliveryTag={DeliveryTag}", delivery.DeliveryTag);
                        channel.BasicReject(delivery.DeliveryTag, false);
                    } catch (Exception exception) {
                        logger.LogError(exception, "Error procesando empleado; deliveryTag={DeliveryTag}", delivery.DeliveryTag);
                        channel.BasicNack(delivery.DeliveryTag, false, true);
                    }
                };
                channel.BasicConsume("vacaciones.empleados", false, "", false, false, null, consumer);
                logger.LogInformation("Consumidor de replica de empleados conectado");
                while (connection.IsOpen && channel.IsOpen && !stoppingToken.IsCancellationRequested)
                    await Task.Delay(1000, stoppingToken);
            } catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) {
                return;
            } catch (Exception exception) {
                logger.LogError(exception, "Consumidor de replica desconectado; reintentando");
                await Task.Delay(2000, stoppingToken);
            }
        }
    }
}

public static class EmployeeEventProjection {
    private static string Required(JsonElement data, string name) {
        if (!data.TryGetProperty(name, out var value) || value.ValueKind != JsonValueKind.String || string.IsNullOrWhiteSpace(value.GetString()))
            throw new ArgumentException($"Falta {name}");
        return value.GetString()!;
    }

    public static (string EmployeeId, string Email, string State) Validate(EmployeeEvent message) {
        if (message.Id == Guid.Empty || message.Version != 1 || message.Producer != "empleados-service")
            throw new ArgumentException("Envelope invalido");
        if (!DateTimeOffset.TryParse(message.OccurredAt, out var occurred) || occurred.Offset != TimeSpan.Zero)
            throw new ArgumentException("occurredAt invalido");
        if (message.Data.ValueKind != JsonValueKind.Object) throw new ArgumentException("data invalida");
        var employeeId = Required(message.Data, "empleadoId");
        var email = Required(message.Data, "email");
        if (message.Type == "empleado.creado") {
            Required(message.Data, "nombre"); Required(message.Data, "apellido");
            Required(message.Data, "numeroEmpleado"); Required(message.Data, "cargo");
            Required(message.Data, "area"); Required(message.Data, "departamentoId");
            Required(message.Data, "fechaIngreso");
            if (Required(message.Data, "estado") != "ACTIVO") throw new ArgumentException("Estado inicial invalido");
            return (employeeId, email, "ACTIVO");
        }
        if (message.Type == "empleado.retirado") {
            if (!DateTimeOffset.TryParse(Required(message.Data, "fechaRetiro"), out var retirement) || retirement.Offset != TimeSpan.Zero)
                throw new ArgumentException("fechaRetiro invalida");
            Required(message.Data, "motivo");
            return (employeeId, email, "RETIRADO");
        }
        if (message.Type == "empleado.actualizado") {
            Required(message.Data, "nombre"); Required(message.Data, "apellido");
            Required(message.Data, "cargo"); Required(message.Data, "area"); Required(message.Data, "departamentoId");
            return (employeeId, email, "ACTUALIZADO");
        }
        throw new ArgumentException("Tipo de evento no soportado");
    }
}
