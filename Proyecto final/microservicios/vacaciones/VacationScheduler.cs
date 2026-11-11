using System.Diagnostics;

public record ScheduledTransition(Vacacion Vacation, string Email);
public record ScheduleRun(int Started, int Finished);

public interface IVacationScheduleStore {
    Task<IReadOnlyList<string>> DueIds(string state, DateOnly today);
    Task<ScheduledTransition?> TransitionIfDue(string id, string expectedState, DateOnly today);
}

public interface IVacationEventsPublisher {
    void PublishStarted(Vacacion vacation, string email);
    void PublishFinished(Vacacion vacation, string email);
}

public sealed class VacationScheduler(
    IVacationScheduleStore store,
    IVacationEventsPublisher publisher,
    TimeProvider clock,
    ILogger<VacationScheduler> logger) : BackgroundService {

    public static int IntervalSeconds() {
        var text = Environment.GetEnvironmentVariable("VACACIONES_SCHEDULER_INTERVAL_SECONDS") ?? "60";
        if (!int.TryParse(text, out var seconds) || seconds < 1 || seconds > 3600)
            throw new InvalidOperationException("VACACIONES_SCHEDULER_INTERVAL_SECONDS debe estar entre 1 y 3600");
        return seconds;
    }

    public async Task<ScheduleRun> RunOnce(DateOnly today) {
        var started = 0;
        var finished = 0;
        foreach (var id in await store.DueIds("EN_CURSO", today)) {
            // Reto 8: no hay petición HTTP que origine la traza -> span RAÍZ manual por vacación
            using var activity = StartRootSpan("scheduler.vacaciones.finalizar", id);
            var transition = await store.TransitionIfDue(id, "EN_CURSO", today);
            if (transition is null) { activity?.SetTag("scheduler.resultado", "sin_cambio"); continue; }
            finished++;
            activity?.SetTag("empleado.id", transition.Vacation.EmpleadoId);
            logger.LogInformation("Vacaciones finalizadas {VacacionesId} para {EmployeeId}", id, transition.Vacation.EmpleadoId);
            try { publisher.PublishFinished(transition.Vacation, transition.Email); }
            catch (Exception exception) {
                activity?.SetStatus(ActivityStatusCode.Error, exception.Message);
                logger.LogError(exception, "No se pudo publicar vacaciones.finalizadas para {Id} tras commit", id);
            }
        }
        // Finalizar primero evita cerrar en el mismo ciclo una vacación de un solo día que acaba de iniciar.
        foreach (var id in await store.DueIds("PROGRAMADA", today)) {
            // Reto 8: span raíz -> publish (traceparent en headers) -> auth-service -> notificaciones-service
            using var activity = StartRootSpan("scheduler.vacaciones.iniciar", id);
            var transition = await store.TransitionIfDue(id, "PROGRAMADA", today);
            if (transition is null) { activity?.SetTag("scheduler.resultado", "sin_cambio"); continue; }
            started++;
            activity?.SetTag("empleado.id", transition.Vacation.EmpleadoId);
            logger.LogInformation("Vacaciones iniciadas {VacacionesId} para {EmployeeId}", id, transition.Vacation.EmpleadoId);
            try { publisher.PublishStarted(transition.Vacation, transition.Email); }
            catch (Exception exception) {
                activity?.SetStatus(ActivityStatusCode.Error, exception.Message);
                logger.LogError(exception, "No se pudo publicar vacaciones.iniciadas para {Id} tras commit", id);
            }
        }
        return new ScheduleRun(started, finished);
    }

    private static Activity? StartRootSpan(string name, string vacationId) {
        // parentContext = default + Activity.Current = null garantiza que sea la raíz de una traza nueva
        Activity.Current = null;
        var activity = Telemetry.Source.StartActivity(name, ActivityKind.Internal, parentContext: default);
        activity?.SetTag("vacaciones.id", vacationId);
        return activity;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken) {
        using var timer = new PeriodicTimer(TimeSpan.FromSeconds(IntervalSeconds()), clock);
        while (!stoppingToken.IsCancellationRequested) {
            try { await RunOnce(DateOnly.FromDateTime(clock.GetUtcNow().UtcDateTime)); }
            catch (Exception exception) { logger.LogError(exception, "Error en scheduler de vacaciones"); }
            try {
                if (!await timer.WaitForNextTickAsync(stoppingToken)) return;
            } catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { return; }
        }
    }
}
