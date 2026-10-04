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
            var transition = await store.TransitionIfDue(id, "EN_CURSO", today);
            if (transition is null) continue;
            finished++;
            try { publisher.PublishFinished(transition.Vacation, transition.Email); }
            catch (Exception exception) { logger.LogError(exception, "No se pudo publicar vacaciones.finalizadas para {Id} tras commit", id); }
        }
        // Finalizar primero evita cerrar en el mismo ciclo una vacación de un solo día que acaba de iniciar.
        foreach (var id in await store.DueIds("PROGRAMADA", today)) {
            var transition = await store.TransitionIfDue(id, "PROGRAMADA", today);
            if (transition is null) continue;
            started++;
            try { publisher.PublishStarted(transition.Vacation, transition.Email); }
            catch (Exception exception) { logger.LogError(exception, "No se pudo publicar vacaciones.iniciadas para {Id} tras commit", id); }
        }
        return new ScheduleRun(started, finished);
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
