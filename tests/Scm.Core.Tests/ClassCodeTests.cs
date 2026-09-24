using Scm.Core.Model;

namespace Scm.Core.Tests;

public class ClassCodeTests
{
    [Theory]
    [InlineData("4a")]
    [InlineData("11b")]
    public void AcceptsValid(string value)
    {
        new ClassCode(value).Value.Should().Be(value);
    }

    [Theory]
    [InlineData("..")]
    [InlineData("../4a")]
    [InlineData("4a/..")]
    [InlineData("4A")]
    [InlineData("4-А")]
    [InlineData("123a")]
    [InlineData("4ab")]
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
