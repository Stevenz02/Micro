using System.Globalization;
using System.Text;
using System.Text.Json;
using RabbitMQ.Client;

public sealed class RabbitPublisher {
    public static ConnectionFactory Factory() {
        foreach (var key in new[] { "RABBITMQ_HOST", "RABBITMQ_USER", "RABBITMQ_PASSWORD" })
            if (string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(key)))
                throw new InvalidOperationException($"Falta la variable {key}");
        return new ConnectionFactory {
            HostName = Environment.GetEnvironmentVariable("RABBITMQ_HOST"),
            UserName = Environment.GetEnvironmentVariable("RABBITMQ_USER"),
            Password = Environment.GetEnvironmentVariable("RABBITMQ_PASSWORD"),
            RequestedHeartbeat = TimeSpan.FromSeconds(20),
            AutomaticRecoveryEnabled = true,
            DispatchConsumersAsync = true,
            ContinuationTimeout = TimeSpan.FromSeconds(5),
        };
    }

    public void PublishScheduled(Vacacion vacation, string email) {
        var id = Guid.NewGuid().ToString();
        var body = JsonSerializer.SerializeToUtf8Bytes(new {
            id,
            type = "vacaciones.programadas",
            version = 1,
            occurredAt = DateTimeOffset.UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffZ", CultureInfo.InvariantCulture),
            producer = "vacaciones-service",
            data = new {
                vacacionesId = vacation.Id,
                empleadoId = vacation.EmpleadoId,
                email,
                fechaInicio = vacation.FechaInicio.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture),
                fechaFin = vacation.FechaFin.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture),
                diasHabiles = VacationRules.BusinessDays(vacation.FechaInicio, vacation.FechaFin),
            },
        });
        using var connection = Factory().CreateConnection();
        using var channel = connection.CreateModel();
        var returned = false;
        channel.BasicReturn += (_, _) => returned = true;
        channel.ConfirmSelect();
        var properties = channel.CreateBasicProperties();
        properties.ContentType = "application/json";
        properties.DeliveryMode = 2;
        properties.MessageId = id;
        properties.Type = "vacaciones.programadas";
        channel.BasicPublish("rrhh.events", "vacaciones.programadas", true, properties, body);
        channel.WaitForConfirmsOrDie(TimeSpan.FromSeconds(5));
        if (returned) throw new InvalidOperationException("El evento vacaciones.programadas no tuvo ruta en RabbitMQ");
    }
}
