namespace Vacaciones.Contratos;

/// <summary>Cuerpo de PUT /vacaciones/{id}: nuevas fechas de un período que aún no inicia.</summary>
public record VacacionReprogramacion(DateOnly FechaInicio, DateOnly FechaFin);
