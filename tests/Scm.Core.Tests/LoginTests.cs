using Scm.Core.Model;

namespace Scm.Core.Tests;

public class LoginTests
{
    [Theory]
    [InlineData("ivanenko.petro.2011", true)]
    [InlineData("kovalenko.a.2011", true)]
    [InlineData("ivanenko.p.o.2011", true)]
    [InlineData("bilyi-chornyi.a.2012", true)]
    [InlineData("viktor.admin", false)]
    [InlineData("v.prizvyshche", false)]
    public void AcceptsStudentAndTeacherLogins(string value, bool isStudent)
    {
        var login = new Login(value);

        login.Value.Should().Be(value);
        login.IsStudent.Should().Be(isStudent);
    }

    [Theory]
    [InlineData("..")]
    [InlineData("ivanenko..petro.2011")]
    [InlineData("../ivanenko.petro.2011")]
    [InlineData("ivanenko.petro.2011\\x")]
    [InlineData("ivanenko.pe tro.2011")]
    [InlineData("Ivanenko.Petro.2011")]
    [InlineData("іваненко.петро.2011")]
    [InlineData("ivanenko.petro.2011;rm")]
    [InlineData("ivanenko.petro.11")]
    [InlineData("ivanenko.petro.1811")]
    [InlineData("ivanenko.petro.2011.2")]
    [InlineData("kovalenko.anastasiia.2011")]
    [InlineData("kovalenko-shevchenko.a.2012")]
    [InlineData("4a.ivanenko")]
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
