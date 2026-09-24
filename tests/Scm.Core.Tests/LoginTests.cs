using Scm.Core.Model;

namespace Scm.Core.Tests;

public class LoginTests
{
    [Theory]
    [InlineData("4a.ivanenko", true)]
    [InlineData("11b.kovalenko.m", true)]
    [InlineData("viktor.admin", false)]
    public void AcceptsStudentAndTeacherLogins(string value, bool isStudent)
    {
        var login = new Login(value);

        login.Value.Should().Be(value);
        login.IsStudent.Should().Be(isStudent);
    }

    [Theory]
    [InlineData("..")]
    [InlineData("4a..ivanenko")]
    [InlineData("../4a.ivanenko")]
    [InlineData("4a.ivanenko\\x")]
    [InlineData("4a.iva nenko")]
    [InlineData("4A.Ivanenko")]
    [InlineData("4a.іваненко")]
    [InlineData("4a.ivanenko;rm")]
    public void RejectsInvalid(string value)
    {
        var act = () => new Login(value);

        act.Should().Throw<ArgumentException>();
    }

    [Theory]
    [InlineData("")]
    [InlineData(" ")]
    public void RejectsEmpty(string value)
    {
        var act = () => new Login(value);

        act.Should().Throw<ArgumentException>();
    }
}
