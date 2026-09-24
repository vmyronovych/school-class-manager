using NSubstitute;
using Scm.Core.Model;
using Scm.Infrastructure.Process;

namespace Scm.Infrastructure.Tests.Process;

public class SudoAccountCommandsTests
{
    private const string Password = "kit1-Ab";

    private readonly IProcessRunner _runner = Substitute.For<IProcessRunner>();
    private readonly SudoAccountCommands _commands;
    private ProcessSpec? _spec;

    public SudoAccountCommandsTests()
    {
        _runner.RunAsync(Arg.Do<ProcessSpec>(s => _spec = s), Arg.Any<CancellationToken>())
            .Returns(new ProcessResult(0, "", "", TimedOut: false));
        _commands = new SudoAccountCommands(new SudoRunner(_runner));
    }

    private IEnumerable<string> ScmUserArguments => _spec!.Arguments.Skip(2);

    [Fact]
    public async Task CreatePassesCyrillicAndQuotedNamesAsSingleArgumentsAndPasswordOnlyViaStdin()
    {
        var student = new NewStudent(new Login("obrajen.anna.2014"), "О'Брайен \"Мол.\"", "Анна-Марія", new ClassCode("2025-4a"));

        var result = await _commands.CreateAsync(student, Password, CancellationToken.None);

        result.IsSuccess.Should().BeTrue();
        _spec!.Arguments.Take(2).Should().Equal("-n", "/usr/local/sbin/scm-user");
        ScmUserArguments.Should().Equal(
            "create", "obrajen.anna.2014", "--class", "2025-4a", "--given-name", "Анна-Марія", "--surname", "О'Брайен \"Мол.\"");
        _spec.StandardInput.Should().Be(Password + "\n");
        _spec.Arguments.Should().NotContain(a => a.Contains(Password, StringComparison.Ordinal));
    }

    [Fact]
    public async Task SetPasswordForStudentHasNoTeacherFlag()
    {
        await _commands.SetPasswordAsync(new Login("ivanenko.petro.2011"), Password, CancellationToken.None);

        ScmUserArguments.Should().Equal("setpassword", "ivanenko.petro.2011");
        _spec!.StandardInput.Should().Be(Password + "\n");
    }

    [Fact]
    public async Task TeacherLoginGetsTeacherFlag()
    {
        await _commands.SetPasswordAsync(new Login("olena.petrenko"), Password, CancellationToken.None);

        ScmUserArguments.Should().Equal("setpassword", "olena.petrenko", "--teacher");
    }

    [Theory]
    [InlineData(true, "enable")]
    [InlineData(false, "disable")]
    public async Task SetEnabledMapsToEnableOrDisable(bool enabled, string op)
    {
        await _commands.SetEnabledAsync(new Login("lysenko.ivan.2015"), enabled, CancellationToken.None);

        ScmUserArguments.Should().Equal(op, "lysenko.ivan.2015");
        _spec!.StandardInput.Should().BeNull();
    }

    [Fact]
    public async Task UnlockAndEnroll()
    {
        await _commands.UnlockAsync(new Login("bondar.oleksii.2014"), CancellationToken.None);
        ScmUserArguments.Should().Equal("unlock", "bondar.oleksii.2014");

        await _commands.EnrollAsync(new Login("bondar.oleksii.2014"), new ClassCode("2026-5a"), CancellationToken.None);
        ScmUserArguments.Should().Equal("enroll", "bondar.oleksii.2014", "2026-5a");
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("kit1\n--teacher")]
    [InlineData("kit1\0")]
    public async Task RejectsEmptyOrMultilinePasswordWithoutRunningAnything(string password)
    {
        var act = () => _commands.SetPasswordAsync(new Login("ivanenko.petro.2011"), password, CancellationToken.None);

        await act.Should().ThrowAsync<ArgumentException>();
        await _runner.DidNotReceiveWithAnyArgs().RunAsync(default!, default);
    }

    [Theory]
    [InlineData("", "Петро")]
    [InlineData("Іваненко", " ")]
    [InlineData("Іваненко\nX", "Петро")]
    public async Task RejectsEmptyOrMultilineNames(string surname, string givenName)
    {
        var student = new NewStudent(new Login("ivanenko.petro.2011"), surname, givenName, new ClassCode("2025-4a"));

        var act = () => _commands.CreateAsync(student, Password, CancellationToken.None);

        await act.Should().ThrowAsync<ArgumentException>();
        await _runner.DidNotReceiveWithAnyArgs().RunAsync(default!, default);
    }

    [Fact]
    public async Task TeacherCannotBeCreatedOrEnrolledAsStudent()
    {
        var teacher = new Login("olena.petrenko");

        var create = () => _commands.CreateAsync(new NewStudent(teacher, "Петренко", "Олена", new ClassCode("2025-4a")), Password, CancellationToken.None);
        var enroll = () => _commands.EnrollAsync(teacher, new ClassCode("2025-4a"), CancellationToken.None);

        await create.Should().ThrowAsync<ArgumentException>();
        await enroll.Should().ThrowAsync<ArgumentException>();
        await _runner.DidNotReceiveWithAnyArgs().RunAsync(default!, default);
    }

    [Theory]
    [InlineData("Administrator")]
    [InlineData("admin")]
    [InlineData("root")]
    [InlineData("ivanenko.petro.2011 --teacher")]
    [InlineData("-n")]
    [InlineData("--teacher")]
    public void ForbiddenLoginsNeverReachTheWrapper(string value)
    {
        var act = () => new Login(value);

        act.Should().Throw<ArgumentException>();
    }

    [Fact]
    public async Task WrapperRefusalBecomesFailureWithStderrAsDetails()
    {
        _runner.RunAsync(default!, default).ReturnsForAnyArgs(
            new ProcessResult(2, "", "scm-user: refused: target is in Domain Admins\n", TimedOut: false));

        var result = await _commands.UnlockAsync(new Login("viktor.admin"), CancellationToken.None);

        result.IsSuccess.Should().BeFalse();
        result.Error!.Code.Should().Be("scm-user.failed");
        result.Error.Details.Should().Be("scm-user: refused: target is in Domain Admins");
    }

    [Fact]
    public async Task TimeoutBecomesFailureWithoutPassword()
    {
        _runner.RunAsync(default!, default).ReturnsForAnyArgs(new ProcessResult(-1, "", "", TimedOut: true));

        var result = await _commands.SetPasswordAsync(new Login("ivanenko.petro.2011"), Password, CancellationToken.None);

        result.Error!.Code.Should().Be("scm-user.timeout");
        result.Error.ToString().Should().NotContain(Password);
    }
}
