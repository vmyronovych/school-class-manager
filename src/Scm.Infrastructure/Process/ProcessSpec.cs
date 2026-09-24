namespace Scm.Infrastructure.Process;

/// <summary>Що запустити: програма, аргументи (кожен окремо, без shell), stdin і таймаут.</summary>
public sealed record ProcessSpec(string FileName, IReadOnlyList<string> Arguments, string? StandardInput, TimeSpan Timeout);

public sealed record ProcessResult(int ExitCode, string StandardOutput, string StandardError, bool TimedOut)
{
    public bool Succeeded => !TimedOut && ExitCode == 0;
}
