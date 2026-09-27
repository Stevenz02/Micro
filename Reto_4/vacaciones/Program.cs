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

var app = builder.Build();
app.UseSwagger(c => c.RouteTemplate = "vacaciones/{documentName}/openapi.json");
app.UseSwaggerUI(c => { c.RoutePrefix = "vacaciones/docs"; c.SwaggerEndpoint("/vacaciones/v1/openapi.json", "Vacaciones v4"); });

app.MapGet("/health", async (NpgsqlDataSource db) => {
    try { await using var cmd = db.CreateCommand("SELECT 1"); await cmd.ExecuteScalarAsync(); return Results.Ok(new { status = "ok" }); }
    catch { return Results.Json(new { detail = "Base de datos no disponible" }, statusCode: 503); }
});

app.MapPost("/vacaciones", async (VacacionRequest request, VacacionesRepository repo) => {
    var dateError = VacationRules.ValidateDates(request.FechaInicio, request.FechaFin, DateOnly.FromDateTime(DateTime.UtcNow));
    if (dateError is not null) return Results.BadRequest(new { detail = dateError });
    var employee = await repo.EmployeeStatus(request.EmpleadoId);
    if (employee is null) return Results.BadRequest(new { detail = $"El empleado {request.EmpleadoId} no existe en la replica local" });
    if (employee == "RETIRADO") return Results.BadRequest(new { detail = $"El empleado {request.EmpleadoId} esta retirado" });
    var conflict = await repo.FindConflict(request.EmpleadoId, request.FechaInicio, request.FechaFin);
    if (conflict is not null) return Results.BadRequest(new { detail = $"El periodo se solapa con {conflict.FechaInicio:yyyy-MM-dd} a {conflict.FechaFin:yyyy-MM-dd}" });
    try { return Results.Created($"/vacaciones/{request.Id}", await repo.Create(request)); }
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

public record VacacionRequest(string Id, string EmpleadoId, DateOnly FechaInicio, DateOnly FechaFin);
public record Vacacion(string Id, string EmpleadoId, DateOnly FechaInicio, DateOnly FechaFin, string Estado, DateTimeOffset FechaCreacion);

public static class VacationRules {
    public static string? ValidateDates(DateOnly start, DateOnly end, DateOnly today) {
        if (end <= start) return "fechaFin debe ser posterior a fechaInicio";
        if (start < today) return "fechaInicio no puede estar en el pasado";
        return null;
    }
    public static bool Overlaps(DateOnly newStart, DateOnly newEnd, DateOnly existingStart, DateOnly existingEnd) => newStart <= existingEnd && newEnd >= existingStart;
}

public sealed class VacacionesRepository(NpgsqlDataSource db) {
    private const string Columns = "id,empleado_id,fecha_inicio,fecha_fin,estado,fecha_creacion";
    private static Vacacion Read(NpgsqlDataReader r) => new(r.GetString(0), r.GetString(1), r.GetFieldValue<DateOnly>(2), r.GetFieldValue<DateOnly>(3), r.GetString(4), r.GetFieldValue<DateTimeOffset>(5));
    public async Task<string?> EmployeeStatus(string id) {
        await using var cmd = db.CreateCommand("SELECT estado FROM empleados_replica WHERE empleado_id=$1"); cmd.Parameters.AddWithValue(id); return (string?)await cmd.ExecuteScalarAsync();
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
