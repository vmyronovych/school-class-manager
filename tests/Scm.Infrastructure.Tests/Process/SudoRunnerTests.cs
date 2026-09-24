using NSubstitute;
using Scm.Infrastructure.Process;

namespace Scm.Infrastructure.Tests.Process;

public class SudoRunnerTests
{
    private static readonly string[] ExpectedLogsArguments = ["-n", "/usr/local/sbin/scm-logs", "samba-ad-dc", "a b"];

    [Theory]
    [InlineData(SudoProgram.ScmUser, "/usr/local/sbin/scm-user")]
    [InlineData(SudoProgram.ScmStatus, "/usr/local/sbin/scm-status")]
    [InlineData(SudoProgram.ScmLogs, "/usr/local/sbin/scm-logs")]
    [InlineData(SudoProgram.Snap, "/usr/local/sbin/snap.sh")]
    [InlineData(SudoProgram.Backup, "/usr/local/sbin/backup.sh")]
    public void RunsWhitelistedProgramNonInteractively(SudoProgram program, string path)
    {
        SudoRunner.BuildArguments(program, ["x"]).Should().Equal("-n", path, "x");
    }

    [Fact]
    public void ScmUpdateIsFixedSystemctlCommandWithoutExtraArguments()
    {
        SudoRunner.BuildArguments(SudoProgram.ScmUpdate, [])
            .Should().Equal("-n", "/usr/bin/systemctl", "start", "scm-update.service");

        var act = () => SudoRunner.BuildArguments(SudoProgram.ScmUpdate, ["scm.service"]);
        act.Should().Throw<ArgumentException>();
    }

    [Fact]
    public void RejectsProgramOutsideWhitelist()
    {
        var act = () => SudoRunner.BuildArguments((SudoProgram)99, []);

        act.Should().Throw<ArgumentOutOfRangeException>();
    }

    [Fact]
    public async Task StartsSudoWithArgumentsAsSeparateItems()
    {
        var runner = Substitute.For<IProcessRunner>();
        var sudo = new SudoRunner(runner);

        await sudo.RunAsync(SudoProgram.ScmLogs, ["samba-ad-dc", "a b"], CancellationToken.None);

        await runner.Received(1).RunAsync(
            Arg.Is<ProcessSpec>(s =>
                s.FileName == "/usr/bin/sudo" &&
                s.Arguments.SequenceEqual(ExpectedLogsArguments) &&
                s.StandardInput == null &&
                s.Timeout == SudoRunner.DefaultTimeout),
            Arg.Any<CancellationToken>());
    }

    [Fact]
    public async Task RejectsNulInArgument()
    {
        var sudo = new SudoRunner(Substitute.For<IProcessRunner>());

        var act = () => sudo.RunAsync(SudoProgram.ScmUser, ["unlock", "4a.x\0--teacher"], CancellationToken.None);

        await act.Should().ThrowAsync<ArgumentException>();
    }
}
