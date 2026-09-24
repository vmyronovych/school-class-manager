using Scm.Core.Model;

namespace Scm.Core.Tests;

public class StorePathTests
{
    [Theory]
    [InlineData(Share.Home, "4a.ivanenko/Documents")]
    [InlineData(Share.Home, "4a.ivanenko/Documents/Відновлено 24.09.2026/звіт.docx")]
    [InlineData(Share.Class, "4a/handouts/..txt")]
    public void AcceptsRelativePathInsideShare(Share share, string relative)
    {
        var path = new StorePath(share, relative);

        path.Share.Should().Be(share);
        path.Relative.Should().Be(relative);
    }

    [Theory]
    [InlineData("..")]
    [InlineData("../etc/passwd")]
    [InlineData("4a.ivanenko/../4a.kovalenko")]
    [InlineData("4a.ivanenko/..")]
    [InlineData("./4a.ivanenko")]
    [InlineData("/etc/passwd")]
    [InlineData("4a.ivanenko\\..\\x")]
    [InlineData("4a.ivanenko//Documents")]
    [InlineData("4a.ivanenko/Documents/")]
    [InlineData("4a.ivanenko/ /x")]
    [InlineData("4a.ivanenko/a\0b")]
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
