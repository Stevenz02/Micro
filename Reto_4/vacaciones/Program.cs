using Npgsql;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();
var required = new[] { "DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD" };
foreach (var key in required)
    if (string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(key)))
        throw new InvalidOperationException($"Falta la variable {key}");
var connection = new NpgsqlConnectionStringBuilder {
    Host = Environment.GetEnvironmentVariable("DB_HOST"),
    Port = int.Parse(Environment.GetEnvironmentVariable("DB_PORT") ?? "5432"),
    Database = Environment.GetEnvironmentVariable("DB_NAME"),
    Username = Environment.GetEnvironmentVariable("DB_USER"),
    Password = Environment.GetEnvironmentVariable("DB_PASSWORD"),
    Timeout = 5,
    CommandTimeout = 5,
}.ConnectionString;
builder.Services.AddSingleton(new NpgsqlDataSourceBuilder(connection).Build());
builder.Services.AddSingleton<VacacionesRepository>();
builder.Services.AddSingleton<RabbitPublisher>();
builder.Services.AddHostedService<EmployeeEventsConsumer>();

var app = builder.Build();
await app.Services.GetRequiredService<VacacionesRepository>().EnsureSchema();
app.UseSwagger(c => c.RouteTemplate = "vacaciones/{documentName}/openapi.json");
app.UseSwaggerUI(c => { c.RoutePrefix = "vacaciones/docs"; c.SwaggerEndpoint("/vacaciones/v1/openapi.json", "Vacaciones v4"); });

app.MapGet("/health", async (NpgsqlDataSource db) => {
    try { await using var cmd = db.CreateCommand("SELECT 1"); await cmd.ExecuteScalarAsync(); return Results.Ok(new { status = "ok" }); }
    catch { return Results.Json(new { detail = "Base de datos no disponible" }, statusCode: 503); }
});

app.MapPost("/vacaciones", async (VacacionRequest request, VacacionesRepository repo, RabbitPublisher publisher, ILogger<Program> logger) => {
    if (string.IsNullOrWhiteSpace(request.Id)) {
        var generatedId = $"V-{DateTime.UtcNow:yyyy}-{Guid.NewGuid().ToString("N")[..6].ToUpperInvariant()}";
        request = request with { Id = generatedId };
    }
    var dateError = VacationRules.ValidateDates(request.FechaInicio, request.FechaFin, DateOnly.FromDateTime(DateTime.UtcNow));
    if (dateError is not null) return Results.BadRequest(new { detail = dateError });
    var employee = await repo.GetEmployee(request.EmpleadoId);
    if (employee is null) return Results.BadRequest(new { detail = $"El empleado {request.EmpleadoId} no existe en la replica local" });
    if (employee.Estado == "RETIRADO") return Results.BadRequest(new { detail = $"El empleado {request.EmpleadoId} esta retirado" });
    if (string.IsNullOrWhiteSpace(employee.Email)) return Results.BadRequest(new { detail = "La replica del empleado no tiene email para el evento oficial" });
    var conflict = await repo.FindConflict(request.EmpleadoId, request.FechaInicio, request.FechaFin);
    if (conflict is not null) return Results.BadRequest(new { detail = $"El periodo se solapa con {conflict.FechaInicio:yyyy-MM-dd} a {conflict.FechaFin:yyyy-MM-dd}" });
    try {
        var created = await repo.Create(request);
        try { publisher.PublishScheduled(created, employee.Email); }
        catch (Exception exception) { logger.LogError(exception, "No se pudo publicar vacaciones.programadas para {Id} tras commit de BD", created.Id); }
        return Results.Created($"/vacaciones/{request.Id}", created);
    }
    catch (PostgresException ex) when (ex.SqlState == PostgresErrorCodes.UniqueViolation) { return Results.BadRequest(new { detail = $"La vacacion {request.Id} ya existe" }); }
}).Produces<Vacacion>(201).Produces(400);

app.MapGet("/vacaciones", async (string? empleadoId, VacacionesRepository repo) => Results.Ok(await repo.List(empleadoId)));
app.MapGet("/vacaciones/{id}", async (string id, VacacionesRepository repo) => {
    var item = await repo.Get(id); return item is null ? Results.NotFound(new { detail = $"La vacacion {id} no existe" }) : Results.Ok(item);
}).Produces<Vacacion>().Produces(404);
app.MapDelete("/vacaciones/{id}", async (string id, VacacionesRepository repo) => {
    var current = await repo.Get(id);
    if (current is null) return Results.NotFound(new { detail = $"La vacacion {id} no existe" });
    if (current.Estado == "CANCELADA") return Results.BadRequest(new { detail = "La vacacion ya esta cancelada" });
    if (current.FechaInicio <= DateOnly.FromDateTime(DateTime.UtcNow)) return Results.BadRequest(new { detail = "No se puede cancelar una vacacion que ya inicio" });
    return Results.Ok(await repo.Cancel(id));
}).Produces<Vacacion>().Produces(400).Produces(404);

app.Run();

public record VacacionRequest(string? Id, string EmpleadoId, DateOnly FechaInicio, DateOnly FechaFin);
public record Vacacion(string Id, string EmpleadoId, DateOnly FechaInicio, DateOnly FechaFin, string Estado, DateTimeOffset FechaCreacion);
public record EmpleadoReplica(string Estado, string? Email);

public static class VacationRules {
    public static string? ValidateDates(DateOnly start, DateOnly end, DateOnly today) {
        if (end <= start) return "fechaFin debe ser posterior a fechaInicio";
        if (start < today) return "fechaInicio no puede estar en el pasado";
        return null;
    }
    public static bool Overlaps(DateOnly newStart, DateOnly newEnd, DateOnly existingStart, DateOnly existingEnd) => newStart <= existingEnd && newEnd >= existingStart;
    public static int BusinessDays(DateOnly start, DateOnly end) {
        var count = 0;
        for (var day = start; day <= end; day = day.AddDays(1))
            if (day.DayOfWeek is not (DayOfWeek.Saturday or DayOfWeek.Sunday)) count++;
        return count;
    }
}

public sealed class VacacionesRepository(NpgsqlDataSource db) {
    private const string Columns = "id,empleado_id,fecha_inicio,fecha_fin,estado,fecha_creacion";
    private static Vacacion Read(NpgsqlDataReader r) => new(r.GetString(0), r.GetString(1), r.GetFieldValue<DateOnly>(2), r.GetFieldValue<DateOnly>(3), r.GetString(4), r.GetFieldValue<DateTimeOffset>(5));
    public async Task EnsureSchema() {
        await using var cmd = db.CreateCommand("ALTER TABLE empleados_replica ADD COLUMN IF NOT EXISTS email TEXT");
        await cmd.ExecuteNonQueryAsync();
    }
    public async Task<EmpleadoReplica?> GetEmployee(string id) {
        await using var cmd = db.CreateCommand("SELECT estado,email FROM empleados_replica WHERE empleado_id=$1");
        cmd.Parameters.AddWithValue(id);
        await using var reader = await cmd.ExecuteReaderAsync();
        return await reader.ReadAsync() ? new EmpleadoReplica(reader.GetString(0), reader.IsDBNull(1) ? null : reader.GetString(1)) : null;
    }
    public async Task<bool> ApplyEmployeeEvent(EmployeeEvent message) {
        var (employeeId, email, state) = EmployeeEventProjection.Validate(message);
        await using var connection = await db.OpenConnectionAsync();
        await using var transaction = await connection.BeginTransactionAsync();
        await using var marker = new NpgsqlCommand("INSERT INTO eventos_procesados(id) VALUES($1) ON CONFLICT DO NOTHING", connection, transaction);
        marker.Parameters.AddWithValue(message.Id);
        if (await marker.ExecuteNonQueryAsync() == 0) {
            await transaction.CommitAsync();
            return false;
        }
        var sql = state == "RETIRADO"
            ? "INSERT INTO empleados_replica(empleado_id,estado,email) VALUES($1,'RETIRADO',$2) ON CONFLICT(empleado_id) DO UPDATE SET estado='RETIRADO',email=EXCLUDED.email,actualizado_en=CURRENT_TIMESTAMP"
            : state == "ACTUALIZADO"
                ? "INSERT INTO empleados_replica(empleado_id,estado,email) VALUES($1,'ACTIVO',$2) ON CONFLICT(empleado_id) DO UPDATE SET email=EXCLUDED.email,actualizado_en=CURRENT_TIMESTAMP"
                : "INSERT INTO empleados_replica(empleado_id,estado,email) VALUES($1,'ACTIVO',$2) ON CONFLICT(empleado_id) DO UPDATE SET estado=CASE WHEN empleados_replica.estado='RETIRADO' THEN 'RETIRADO' ELSE 'ACTIVO' END,email=EXCLUDED.email,actualizado_en=CURRENT_TIMESTAMP";
        await using var update = new NpgsqlCommand(sql, connection, transaction);
        update.Parameters.AddWithValue(employeeId);
        update.Parameters.AddWithValue(email);
        await update.ExecuteNonQueryAsync();
        await transaction.CommitAsync();
        return true;
    }
    public async Task<Vacacion?> FindConflict(string employee, DateOnly start, DateOnly end) {
        await using var cmd = db.CreateCommand($"SELECT {Columns} FROM vacaciones WHERE empleado_id=$1 AND estado IN ('PROGRAMADA','EN_CURSO') AND $2 <= fecha_fin AND $3 >= fecha_inicio ORDER BY fecha_inicio LIMIT 1");
        cmd.Parameters.AddWithValue(employee); cmd.Parameters.AddWithValue(start); cmd.Parameters.AddWithValue(end);
        await using var reader = await cmd.ExecuteReaderAsync(); return await reader.ReadAsync() ? Read(reader) : null;
    }
    public async Task<Vacacion> Create(VacacionRequest value) {
        await using var cmd = db.CreateCommand($"INSERT INTO vacaciones(id,empleado_id,fecha_inicio,fecha_fin,estado) VALUES($1,$2,$3,$4,'PROGRAMADA') RETURNING {Columns}");
        cmd.Parameters.AddWithValue(value.Id); cmd.Parameters.AddWithValue(value.EmpleadoId); cmd.Parameters.AddWithValue(value.FechaInicio); cmd.Parameters.AddWithValue(value.FechaFin);
        await using var reader = await cmd.ExecuteReaderAsync(); await reader.ReadAsync(); return Read(reader);
    }
    public async Task<Vacacion?> Get(string id) {
        await using var cmd = db.CreateCommand($"SELECT {Columns} FROM vacaciones WHERE id=$1"); cmd.Parameters.AddWithValue(id); await using var reader = await cmd.ExecuteReaderAsync(); return await reader.ReadAsync() ? Read(reader) : null;
    }
    public async Task<List<Vacacion>> List(string? employee) {
        var sql = $"SELECT {Columns} FROM vacaciones" + (employee is null ? "" : " WHERE empleado_id=$1") + " ORDER BY fecha_inicio,id"; await using var cmd = db.CreateCommand(sql); if (employee is not null) cmd.Parameters.AddWithValue(employee);
        await using var reader = await cmd.ExecuteReaderAsync(); var result = new List<Vacacion>(); while (await reader.ReadAsync()) result.Add(Read(reader)); return result;
    }
    public async Task<Vacacion> Cancel(string id) {
        await using var cmd = db.CreateCommand($"UPDATE vacaciones SET estado='CANCELADA' WHERE id=$1 RETURNING {Columns}"); cmd.Parameters.AddWithValue(id); await using var reader = await cmd.ExecuteReaderAsync(); await reader.ReadAsync(); return Read(reader);
    }
}

public partial class Program { }
