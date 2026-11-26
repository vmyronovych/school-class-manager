using NSubstitute;
using Scm.Core.Ports;
using Scm.Infrastructure.Process;

namespace Scm.Infrastructure.Tests.Process;

public sealed class SambaStudentAdministrationTests
{
    [Fact]
    public async Task ParsesFileMetadataAndBinaryDownloadThroughStdinOnly()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "../../../../../tools/pi-fixtures/panel/files.4.19.5.json");
        var output = await File.ReadAllTextAsync(path);
        var process = Substitute.For<IProcessRunner>();
        process.RunAsync(Arg.Any<ProcessSpec>(), Arg.Any<CancellationToken>()).Returns(new ProcessResult(0, output, "", false));
        var directory = new SambaStudentAdministration(new SudoRunner(process));
        var actor = new TeacherSession("teacher1", "Teacher", "Teacher", "sid");
        var entries = await directory.ListFilesAsync(actor, "student1", "", CancellationToken.None);
        entries.Should().HaveCount(2);
        entries[0].Directory.Should().BeTrue();
        entries[1].Size.Should().Be(12);
        process.RunAsync(Arg.Any<ProcessSpec>(), Arg.Any<CancellationToken>()).Returns(new ProcessResult(0,
            """{"data":{"name":"work.bin","content":"AAH/"}}""", "", false));
        var download = await directory.DownloadAsync(actor, "student1", "lesson/work.bin", CancellationToken.None);
        download.Content.Should().Equal(new byte[] { 0, 1, 255 });
        await process.Received(1).RunAsync(Arg.Is<ProcessSpec>(s => s.Arguments.Count == 2 && s.StandardInput != null &&
            s.StandardInput.Contains("lesson/work.bin") && s.StandardInput.Contains("teacher1")), Arg.Any<CancellationToken>());
    }

    [Fact]
    public async Task PasswordGoesOnlyToStdinAndActorComesFromAuthenticatedResult()
    {
        var process = Substitute.For<IProcessRunner>();
        process.RunAsync(Arg.Any<ProcessSpec>(), Arg.Any<CancellationToken>()).Returns(new ProcessResult(0,
            """{"data":{"login":"teacher1","displayName":"Teacher","role":"Teacher","sid":"test-sid"}}""", "", false));
        var directory = new SambaStudentAdministration(new SudoRunner(process));
        var result = await directory.AuthenticateAsync("Teacher1", "example-only-secret", CancellationToken.None);
        result.Login.Should().Be("teacher1");
        await process.Received(1).RunAsync(Arg.Is<ProcessSpec>(s =>
            s.Arguments.Count == 2 && s.Arguments[1] == "/usr/local/sbin/scm-directory" &&
            s.StandardInput != null && s.StandardInput.Contains("example-only-secret")), Arg.Any<CancellationToken>());
    }

    [Theory]
    [InlineData("../Administrator")]
    [InlineData("student1\nAdministrator")]
    [InlineData("--help")]
    public async Task InvalidTargetNeverReachesProcess(string login)
    {
        var process = Substitute.For<IProcessRunner>();
        var directory = new SambaStudentAdministration(new SudoRunner(process));
        var action = () => directory.ResetAsync(new TeacherSession("teacher1", "Teacher", "Teacher", "sid"), login, CancellationToken.None);
        await action.Should().ThrowAsync<ArgumentException>();
        await process.DidNotReceiveWithAnyArgs().RunAsync(default!, default);
    }

    [Fact]
    public async Task ParsesServerListFixture()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "../../../../../tools/pi-fixtures/panel/list.4.19.5.json");
        var output = await File.ReadAllTextAsync(path);
        var process = Substitute.For<IProcessRunner>();
        process.RunAsync(Arg.Any<ProcessSpec>(), Arg.Any<CancellationToken>()).Returns(new ProcessResult(0, output, "", false));
        var directory = new SambaStudentAdministration(new SudoRunner(process));
        var result = await directory.ListAsync(new TeacherSession("teacher1", "Teacher", "Teacher", "sid"), CancellationToken.None);
        result.Single().Login.Should().Be("student1");
        result.Single().HomeDirectory.Should().Be(@"\\school-server.school.test\student1");
    }
}
