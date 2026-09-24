namespace Scm.Infrastructure.Process;

/// <summary>
/// Єдиний шлях до команд на Pi: <c>sudo -n &lt;програма з білого списку&gt; &lt;аргументи&gt;</c>.
/// Аргументи передаються окремими елементами argv; секрети — лише через stdin.
/// </summary>
public sealed class SudoRunner(IProcessRunner runner)
{
    public const string SudoPath = "/usr/bin/sudo";

    public static readonly TimeSpan DefaultTimeout = TimeSpan.FromSeconds(10);

    public Task<ProcessResult> RunAsync(SudoProgram program, IReadOnlyList<string> arguments, CancellationToken ct) =>
        RunAsync(program, arguments, standardInput: null, DefaultTimeout, ct);

    public Task<ProcessResult> RunAsync(
        SudoProgram program,
        IReadOnlyList<string> arguments,
        string? standardInput,
        TimeSpan timeout,
        CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(arguments);
        if (arguments.Any(a => a is null || a.Contains('\0', StringComparison.Ordinal)))
        {
            throw new ArgumentException("Аргумент не може бути null або містити NUL.", nameof(arguments));
        }

        return runner.RunAsync(new ProcessSpec(SudoPath, BuildArguments(program, arguments), standardInput, timeout), ct);
    }

    public static IReadOnlyList<string> BuildArguments(SudoProgram program, IReadOnlyList<string> arguments)
    {
        ArgumentNullException.ThrowIfNull(arguments);
        if (program == SudoProgram.ScmUpdate && arguments.Count > 0)
        {
            throw new ArgumentException("scm-update запускається без аргументів.", nameof(arguments));
        }

        // -n: ніколи не питати пароль — якщо sudoers не дозволяє, одразу помилка, а не зависання.
        return [.. Prefix(program), .. arguments];
    }

    private static string[] Prefix(SudoProgram program) => program switch
    {
        SudoProgram.ScmUser => ["-n", "/usr/local/sbin/scm-user"],
        SudoProgram.ScmStatus => ["-n", "/usr/local/sbin/scm-status"],
        SudoProgram.ScmLogs => ["-n", "/usr/local/sbin/scm-logs"],
        SudoProgram.Snap => ["-n", "/usr/local/sbin/snap.sh"],
        SudoProgram.Backup => ["-n", "/usr/local/sbin/backup.sh"],
        SudoProgram.ScmUpdate => ["-n", "/usr/bin/systemctl", "start", "scm-update.service"],
        _ => throw new ArgumentOutOfRangeException(nameof(program), program, "Програми немає в білому списку."),
    };
}
