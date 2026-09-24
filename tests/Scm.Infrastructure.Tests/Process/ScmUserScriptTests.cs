using System.Runtime.Versioning;
using Scm.Infrastructure.Process;

namespace Scm.Infrastructure.Tests.Process;

/// <summary>
/// Справжній <c>pi/sbin/scm-user</c> під bash; <c>samba-tool</c> і <c>logger</c> — фейки в PATH.
/// Фейк записує кожен виклик одним рядком (аргументи через <c>|</c>) і відповідає як Samba з
/// <c>viktor.admin</c> у Domain Admins, <c>olena.petrenko</c> у vchyteli, <c>outsider.ivan.2014</c> поза OU=Uchni.
/// </summary>
[UnsupportedOSPlatform("windows")]
public sealed class ScmUserScriptTests : IDisposable
{
    private const string FakeSambaTool = """
        #!/bin/sh
        (IFS='|'; printf '%s\n' "$*") >> "$SCM_TEST_CALLS"
        case "$1 $2" in
          "group listmembers")
            case "$3" in
              "Domain Admins") printf 'Administrator\nviktor.admin\n' ;;
              vchyteli) printf 'olena.petrenko\n' ;;
            esac ;;
          "user show")
            case "$3" in
              outsider.ivan.2014) echo "dn: CN=$3,CN=Users,DC=ad,DC=school,DC=lan" ;;
              *) echo "dn: CN=$3,OU=Uchni,DC=ad,DC=school,DC=lan" ;;
            esac ;;
        esac
        exit 0
        """;

    private readonly string _dir = Directory.CreateTempSubdirectory("scm-user-test-").FullName;
    private readonly string _calls;

    public ScmUserScriptTests()
    {
        _calls = Path.Combine(_dir, "calls.txt");
        WriteExecutable("samba-tool", FakeSambaTool);
        WriteExecutable("logger", "#!/bin/sh\nexit 0\n");
    }

    public void Dispose() => Directory.Delete(_dir, recursive: true);

    [Fact]
    public async Task SetsStudentPasswordReadFromStdin()
    {
        var result = await RunAsync(["setpassword", "ivanenko.petro.2011"], "kit1\n");

        result.ExitCode.Should().Be(0, result.StandardError);
        Mutations().Should().Equal("user|setpassword|ivanenko.petro.2011|--newpassword=kit1");
    }

    [Fact]
    public async Task AcceptsPasswordWithoutTrailingNewline()
    {
        var result = await RunAsync(["setpassword", "ivanenko.petro.2011"], "kit1");

        result.ExitCode.Should().Be(0, result.StandardError);
        Mutations().Should().Equal("user|setpassword|ivanenko.petro.2011|--newpassword=kit1");
    }

    [Fact]
    public async Task CreatesStudentWithCyrillicNamesAndClassGroup()
    {
        var result = await RunAsync(
            ["create", "obrajen.anna.2014", "--class", "2025-4a", "--given-name", "Анна-Марія", "--surname", "О'Брайен"], "kit1\n");

        result.ExitCode.Should().Be(0, result.StandardError);
        Mutations().Should().Equal(
            "user|create|obrajen.anna.2014|kit1|--given-name=Анна-Марія|--surname=О'Брайен|--userou=OU=Uchni",
            "group|addmembers|uchni-2025-4a|obrajen.anna.2014");
    }

    [Fact]
    public async Task TeacherPasswordNeedsTeacherFlag()
    {
        (await RunAsync(["setpassword", "olena.petrenko"], "kit1\n")).StandardError.Should().Contain("bad student login");

        var result = await RunAsync(["setpassword", "olena.petrenko", "--teacher"], "kit1\n");
        result.ExitCode.Should().Be(0, result.StandardError);
        Mutations().Should().Equal("user|setpassword|olena.petrenko|--newpassword=kit1");
    }

    [Theory]
    [InlineData("setpassword", "viktor.admin", "--teacher")]
    [InlineData("unlock", "viktor.admin", "--teacher")]
    [InlineData("disable", "Administrator", "")]
    [InlineData("setpassword", "outsider.ivan.2014", "")]
    [InlineData("setpassword", "4A.Ivanenko", "")]
    [InlineData("setpassword", "ivanenko.petro.2011;id", "")]
    [InlineData("setpassword", "4a.ivanenko", "")]
    [InlineData("setpassword", "kovalenko.anastasiia.2011", "")]
    [InlineData("setpassword", "", "")]
    [InlineData("enroll", "olena.petrenko", "--teacher")]
    [InlineData("move", "ivanenko.petro.2011", "")]
    [InlineData("create", "olena.petrenko", "--teacher")]
    [InlineData("delete", "ivanenko.petro.2011", "")]
    public async Task RefusesForbiddenTargetsAndOps(string op, string login, string flag)
    {
        string[] arguments = flag.Length == 0 ? [op, login] : [op, login, flag];

        var result = await RunAsync(arguments, "kit1\n");

        result.ExitCode.Should().NotBe(0);
        Mutations().Should().BeEmpty();
    }

    [Theory]
    [InlineData("", "empty password")]
    [InlineData("\n", "empty password")]
    public async Task RefusesEmptyPassword(string stdin, string error)
    {
        var result = await RunAsync(["setpassword", "ivanenko.petro.2011"], stdin);

        result.ExitCode.Should().Be(2);
        result.StandardError.Should().Contain(error);
        Mutations().Should().BeEmpty();
    }

    [Theory]
    [InlineData("4a")]
    [InlineData("2025-4A")]
    [InlineData("")]
    public async Task CreateRefusesBadClass(string cls)
    {
        var result = await RunAsync(
            ["create", "ivanenko.petro.2011", "--class", cls, "--given-name", "Петро", "--surname", "Іваненко"], "kit1\n");

        result.StandardError.Should().Contain("bad class");
        Mutations().Should().BeEmpty();
    }

    [Fact]
    public async Task EnrollOnlyAddsToNewClassGroup()
    {
        var result = await RunAsync(["enroll", "bondar.oleksii.2014", "2026-5a"], null);

        result.ExitCode.Should().Be(0, result.StandardError);
        Mutations().Should().Equal("group|addmembers|uchni-2026-5a|bondar.oleksii.2014");
    }

    [Theory]
    [InlineData]
    [InlineData("5a")]
    [InlineData("2026-5a", "2025-4a")]
    public async Task EnrollRefusesBadClass(params string[] classArgs)
    {
        var result = await RunAsync(["enroll", "bondar.oleksii.2014", .. classArgs], null);

        result.StandardError.Should().Contain("bad class");
        Mutations().Should().BeEmpty();
    }

    private static string ScriptPath()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "SchoolClassManager.sln")))
        {
            dir = dir.Parent;
        }

        return Path.Combine(dir?.FullName ?? throw new InvalidOperationException("Корінь репозиторію не знайдено."), "pi", "sbin", "scm-user");
    }

    private Task<ProcessResult> RunAsync(string[] arguments, string? stdin) =>
        new ProcessRunner().RunAsync(
            new ProcessSpec(
                "/usr/bin/env",
                [$"PATH={_dir}:/usr/bin:/bin", $"SCM_TEST_CALLS={_calls}", "/bin/bash", ScriptPath(), .. arguments],
                stdin,
                TimeSpan.FromSeconds(10)),
            CancellationToken.None);

    // Лише змінні виклики: читання (listmembers, show) не рахуються.
    private string[] Mutations() =>
        File.Exists(_calls)
            ? File.ReadAllLines(_calls).Where(l => !l.StartsWith("group|listmembers|", StringComparison.Ordinal) && !l.StartsWith("user|show|", StringComparison.Ordinal)).ToArray()
            : [];

    private void WriteExecutable(string name, string content)
    {
        var path = Path.Combine(_dir, name);
        File.WriteAllText(path, content.ReplaceLineEndings("\n") + "\n");
        File.SetUnixFileMode(path, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
    }
}
