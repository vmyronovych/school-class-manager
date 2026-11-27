using Scm.Core.Model;

namespace Scm.Core.Tests;

public sealed class AccountNameTests
{
    [Fact]
    public void NormalizesDomainLogins() => new AccountName(" Student-2 ").Value.Should().Be("student-2");

    [Theory]
    [InlineData("../other")]
    [InlineData("student$")]
    public void RejectsNonUserNames(string input) =>
        FluentActions.Invoking(() => new AccountName(input)).Should().Throw<ArgumentException>();
}
