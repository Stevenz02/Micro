using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging.Abstractions;
using Xunit;

public class VacationSchedulerTests {
    private static readonly DateOnly Today = new(2026, 10, 4);

    private sealed class FakeStore : IVacationScheduleStore {
        public Dictionary<string, Vacacion> Items { get; } = new();
        public Task<IReadOnlyList<string>> DueIds(string state, DateOnly today) =>
            Task.FromResult<IReadOnlyList<string>>(Items.Values
                .Where(v => v.Estado == state && (state == "PROGRAMADA" ? v.FechaInicio : v.FechaFin) <= today)
                .Select(v => v.Id).ToList());
        public Task<ScheduledTransition?> TransitionIfDue(string id, string expectedState, DateOnly today) {
            var current = Items[id];
            if (current.Estado != expectedState ||
                (expectedState == "PROGRAMADA" ? current.FechaInicio : current.FechaFin) > today)
                return Task.FromResult<ScheduledTransition?>(null);
            var updated = current with { Estado = expectedState == "PROGRAMADA" ? "EN_CURSO" : "FINALIZADA" };
            Items[id] = updated;
            return Task.FromResult<ScheduledTransition?>(new(updated, "empleado@example.test"));
        }
    }

    private sealed class FakePublisher : IVacationEventsPublisher {
        public List<string> Events { get; } = new();
        public void PublishStarted(Vacacion vacation, string email) => Events.Add("vacaciones.iniciadas:" + vacation.Id);
        public void PublishFinished(Vacacion vacation, string email) => Events.Add("vacaciones.finalizadas:" + vacation.Id);
    }

    [Fact]
    public async Task SameDayStartsAndFinishesExactlyOnce() {
        var store = new FakeStore();
        store.Items["V001"] = new("V001", "E001", Today, Today, "PROGRAMADA", DateTimeOffset.UtcNow);
        var publisher = new FakePublisher();
        var scheduler = new VacationScheduler(store, publisher, TimeProvider.System, NullLogger<VacationScheduler>.Instance);
        Assert.Equal(new ScheduleRun(1, 0), await scheduler.RunOnce(Today));
        Assert.Equal("EN_CURSO", store.Items["V001"].Estado);
        Assert.Equal(new[] { "vacaciones.iniciadas:V001" }, publisher.Events);
        Assert.Equal(new ScheduleRun(0, 1), await scheduler.RunOnce(Today));
        Assert.Equal("FINALIZADA", store.Items["V001"].Estado);
        Assert.Equal(new[] { "vacaciones.iniciadas:V001", "vacaciones.finalizadas:V001" }, publisher.Events);
        Assert.Equal(new ScheduleRun(0, 0), await scheduler.RunOnce(Today));
        Assert.Equal(2, publisher.Events.Count);
    }

    [Fact]
    public async Task FuturePeriodsDoNotTransitionEarly() {
        var store = new FakeStore();
        store.Items["V001"] = new("V001", "E001", Today.AddDays(1), Today.AddDays(2), "PROGRAMADA", DateTimeOffset.UtcNow);
        store.Items["V002"] = new("V002", "E001", Today.AddDays(-2), Today.AddDays(1), "EN_CURSO", DateTimeOffset.UtcNow);
        var publisher = new FakePublisher();
        var scheduler = new VacationScheduler(store, publisher, TimeProvider.System, NullLogger<VacationScheduler>.Instance);
        Assert.Equal(new ScheduleRun(0, 0), await scheduler.RunOnce(Today));
        Assert.Empty(publisher.Events);
    }

    [Theory]
    [InlineData("vacaciones.iniciadas", 5, true)]
    [InlineData("vacaciones.finalizadas", 4, false)]
    public void TransitionPayloadMatchesOfficialCatalog(string type, int fields, bool hasStart) {
        var vacation = new Vacacion("V001", "E001", Today, Today.AddDays(1), "EN_CURSO", DateTimeOffset.UtcNow);
        using var document = JsonDocument.Parse(RabbitPublisher.BuildPayload(type, vacation, "empleado@example.test",
            Guid.Parse("10000000-0000-0000-0000-000000000001"), new DateTimeOffset(2026, 10, 4, 12, 0, 0, TimeSpan.Zero)));
        var root = document.RootElement;
        Assert.Equal(type, root.GetProperty("type").GetString());
        Assert.Equal("vacaciones-service", root.GetProperty("producer").GetString());
        Assert.Equal(1, root.GetProperty("version").GetInt32());
        Assert.Equal("2026-10-04T12:00:00.000Z", root.GetProperty("occurredAt").GetString());
        var data = root.GetProperty("data");
        Assert.Equal(fields, data.EnumerateObject().Count());
        Assert.Equal("V001", data.GetProperty("vacacionesId").GetString());
        Assert.Equal("E001", data.GetProperty("empleadoId").GetString());
        Assert.Equal("empleado@example.test", data.GetProperty("email").GetString());
        Assert.Equal(hasStart, data.TryGetProperty("fechaInicio", out _));
    }
}
