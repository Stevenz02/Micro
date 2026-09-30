using System;
using Xunit;

public class VacationRulesTests {
    private static readonly DateOnly Today = new(2026, 9, 27);
    [Fact] public void RejectsEndEqualToStart() => Assert.NotNull(VacationRules.ValidateDates(Today, Today, Today));
    [Fact] public void RejectsEndBeforeStart() => Assert.NotNull(VacationRules.ValidateDates(Today, Today.AddDays(-1), Today));
    [Fact] public void RejectsPastStart() => Assert.NotNull(VacationRules.ValidateDates(Today.AddDays(-1), Today.AddDays(1), Today));
    [Fact] public void AcceptsFutureRange() => Assert.Null(VacationRules.ValidateDates(Today, Today.AddDays(1), Today));
    [Fact] public void CountsBusinessDaysWithoutWeekends() => Assert.Equal(4,
        VacationRules.BusinessDays(new DateOnly(2026, 11, 10), new DateOnly(2026, 11, 15)));
    [Theory]
    [InlineData(10,20,10,20,true)]
    [InlineData(12,18,10,20,true)]
    [InlineData(8,22,10,20,true)]
    [InlineData(5,10,10,20,true)]
    [InlineData(20,25,10,20,true)]
    [InlineData(1,9,10,20,false)]
    [InlineData(21,30,10,20,false)]
    public void InclusiveOverlapCases(int ns, int ne, int es, int ee, bool expected) => Assert.Equal(expected,
        VacationRules.Overlaps(Today.AddDays(ns), Today.AddDays(ne), Today.AddDays(es), Today.AddDays(ee)));
}
