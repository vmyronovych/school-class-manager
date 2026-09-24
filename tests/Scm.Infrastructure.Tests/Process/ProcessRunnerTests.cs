using Scm.Infrastructure.Process;

namespace Scm.Infrastructure.Tests.Process;

// Справжні процеси: /bin/sh лише друкує свій argv, по одному аргументу в рядку в дужках.
public class ProcessRunnerTests
{
    private static readonly TimeSpan Timeout = TimeSpan.FromSeconds(10);
    private readonly ProcessRunner _runner = new();

    [Fact]
    public async Task PassesEveryArgumentVerbatimWithoutShell()
    {
        string[] arguments = ["Іваненко", "О'Брайен", "\"quoted\"", "", "a b", "$(whoami)", "; rm -rf /", "`id`", "*"];

        var result = await RunShAsync("""for a in "$@"; do printf '[%s]\n' "$a"; done""", arguments);

        result.Succeeded.Should().BeTrue(result.StandardError);
        result.StandardOutput.Split('\n', StringSplitOptions.RemoveEmptyEntries)
            .Should().Equal(arguments.Select(a => $"[{a}]"));
    }

    [Fact]
    public async Task WritesStandardInput()
    {
        var result = await _runner.RunAsync(new ProcessSpec("/bin/cat", [], "kit1-Пароль\n", Timeout), CancellationToken.None);

        result.StandardOutput.Should().Be("kit1-Пароль\n");
    }

    [Fact]
    public async Task CapturesExitCodeAndStandardError()
    {
        var result = await RunShAsync("echo 'scm-user: refused' >&2; exit 2", []);

        result.ExitCode.Should().Be(2);
        result.Succeeded.Should().BeFalse();
        result.StandardError.Should().Be("scm-user: refused\n");
    }

    [Fact]
    public async Task KillsProcessOnTimeout()
    {
        var started = DateTime.UtcNow;

        var result = await _runner.RunAsync(
            new ProcessSpec("/bin/sleep", ["30"], null, TimeSpan.FromMilliseconds(200)), CancellationToken.None);

        result.TimedOut.Should().BeTrue();
        result.Succeeded.Should().BeFalse();
        (DateTime.UtcNow - started).Should().BeLessThan(TimeSpan.FromSeconds(5));
    }

    [Fact]
    public async Task ThrowsAndKillsProcessOnCancel()
    {
        using var cts = new CancellationTokenSource(TimeSpan.FromMilliseconds(200));

        var act = () => _runner.RunAsync(new ProcessSpec("/bin/sleep", ["30"], null, Timeout), cts.Token);

        await act.Should().ThrowAsync<OperationCanceledException>();
    }

    [Fact]
    public async Task DoesNotDeadlockOnLargeOutput()
    {
        var result = await RunShAsync("head -c 1000000 /dev/zero | tr '\\0' x; head -c 1000000 /dev/zero | tr '\\0' y >&2", []);

        result.StandardOutput.Should().HaveLength(1_000_000);
        result.StandardError.Should().HaveLength(1_000_000);
    }

    private Task<ProcessResult> RunShAsync(string script, string[] arguments) =>
        _runner.RunAsync(new ProcessSpec("/bin/sh", ["-c", script, "sh", .. arguments], null, Timeout), CancellationToken.None);
}
