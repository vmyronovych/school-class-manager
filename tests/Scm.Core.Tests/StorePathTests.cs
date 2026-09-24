using Scm.Core.Model;

namespace Scm.Core.Tests;

public class StorePathTests
{
    [Theory]
    [InlineData(Share.Home, "ivanenko.petro.2011/Documents")]
    [InlineData(Share.Home, "ivanenko.petro.2011/Documents/Відновлено 24.09.2026/звіт.docx")]
    [InlineData(Share.Class, "2025-4a/handouts/..txt")]
    public void AcceptsRelativePathInsideShare(Share share, string relative)
    {
        var path = new StorePath(share, relative);

        path.Share.Should().Be(share);
        path.Relative.Should().Be(relative);
    }

    [Theory]
    [InlineData("..")]
    [InlineData("../etc/passwd")]
    [InlineData("ivanenko.petro.2011/../kovalenko.a.2011")]
    [InlineData("ivanenko.petro.2011/..")]
    [InlineData("./ivanenko.petro.2011")]
    [InlineData("/etc/passwd")]
    [InlineData("ivanenko.petro.2011\\..\\x")]
    [InlineData("ivanenko.petro.2011//Documents")]
    [InlineData("ivanenko.petro.2011/Documents/")]
    [InlineData("ivanenko.petro.2011/ /x")]
    [InlineData("ivanenko.petro.2011/a\0b")]
    public void RejectsPathsThatCouldLeaveShare(string relative)
    {
        var act = () => new StorePath(Share.Home, relative);

        act.Should().Throw<ArgumentException>();
    }

    [Fact]
    public void RejectsEmpty()
    {
        var act = () => new StorePath(Share.Home, "");

        act.Should().Throw<ArgumentException>();
    }
}
