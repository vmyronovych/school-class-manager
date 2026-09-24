namespace Scm.Infrastructure.Process;

public interface IProcessRunner
{
    /// <summary>
    /// Запускає процес і чекає завершення. Таймаут → процес убито, <see cref="ProcessResult.TimedOut"/> = true.
    /// Скасування <paramref name="ct"/> → процес убито, <see cref="OperationCanceledException"/>.
    /// </summary>
    Task<ProcessResult> RunAsync(ProcessSpec spec, CancellationToken ct);
}
