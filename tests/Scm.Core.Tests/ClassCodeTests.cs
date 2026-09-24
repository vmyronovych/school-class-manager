using Scm.Core.Model;

namespace Scm.Core.Tests;

public class ClassCodeTests
{
    [Theory]
    [InlineData("2025-4a", 2025)]
    [InlineData("2026-11b", 2026)]
    public void AcceptsValid(string value, int schoolYear)
    {
        var code = new ClassCode(value);

        code.Value.Should().Be(value);
        code.SchoolYear.Should().Be(schoolYear);
    }

    [Theory]
    [InlineData("..")]
    [InlineData("../2025-4a")]
    [InlineData("2025-4a/..")]
    [InlineData("4a")]
    [InlineData("2025-4A")]
    [InlineData("2025-4-А")]
    [InlineData("2025-123a")]
    [InlineData("2025-4ab")]
    [InlineData("1999-4a")]
    [InlineData("25-4a")]
    public void RejectsInvalid(string value)
    {
        var act = () => new ClassCode(value);

        act.Should().Throw<ArgumentException>();
    }

    [Theory]
    [InlineData("")]
    [InlineData(" ")]
    public void RejectsEmpty(string value)
    {
        var act = () => new ClassCode(value);

        act.Should().Throw<ArgumentException>();
    }
}
