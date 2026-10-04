using System.Globalization;
using System.Text.Json;
using RabbitMQ.Client;

public sealed class RabbitPublisher : IVacationEventsPublisher {
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

    public static byte[] BuildPayload(string type, Vacacion vacation, string email, Guid id, DateTimeOffset occurredAt) {
        var dates = new {
            vacacionesId = vacation.Id,
            empleadoId = vacation.EmpleadoId,
            email,
            fechaInicio = vacation.FechaInicio.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture),
            fechaFin = vacation.FechaFin.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture),
        };
        object data = type switch {
            "vacaciones.programadas" => new {
                dates.vacacionesId, dates.empleadoId, dates.email, dates.fechaInicio, dates.fechaFin,
                diasHabiles = VacationRules.BusinessDays(vacation.FechaInicio, vacation.FechaFin),
            },
            "vacaciones.iniciadas" => dates,
            "vacaciones.finalizadas" => new { dates.vacacionesId, dates.empleadoId, dates.email, dates.fechaFin },
            _ => throw new ArgumentException("Evento de vacaciones no soportado", nameof(type)),
        };
        return JsonSerializer.SerializeToUtf8Bytes(new {
            id = id.ToString(),
            type,
            version = 1,
            occurredAt = occurredAt.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ", CultureInfo.InvariantCulture),
            producer = "vacaciones-service",
            data,
        });
    }

    public void PublishScheduled(Vacacion vacation, string email) => Publish("vacaciones.programadas", vacation, email);
    public void PublishStarted(Vacacion vacation, string email) => Publish("vacaciones.iniciadas", vacation, email);
    public void PublishFinished(Vacacion vacation, string email) => Publish("vacaciones.finalizadas", vacation, email);

    private static void Publish(string type, Vacacion vacation, string email) {
        var id = Guid.NewGuid();
        var body = BuildPayload(type, vacation, email, id, DateTimeOffset.UtcNow);
        using var connection = Factory().CreateConnection();
        using var channel = connection.CreateModel();
        var returned = false;
        channel.BasicReturn += (_, _) => returned = true;
        channel.ConfirmSelect();
        var properties = channel.CreateBasicProperties();
        properties.ContentType = "application/json";
        properties.DeliveryMode = 2;
        properties.MessageId = id.ToString();
        properties.Type = type;
        channel.BasicPublish("rrhh.events", type, true, properties, body);
        channel.WaitForConfirmsOrDie(TimeSpan.FromSeconds(5));
        if (returned) throw new InvalidOperationException($"El evento {type} no tuvo ruta en RabbitMQ");
    }
}
