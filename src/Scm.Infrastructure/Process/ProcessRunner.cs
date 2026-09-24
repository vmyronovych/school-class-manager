using System.Diagnostics;

namespace Scm.Infrastructure.Process;

/// <summary>
/// Запуск через <see cref="ProcessStartInfo.ArgumentList"/>: кожен аргумент потрапляє в argv як є,
/// без shell і без склеювання в рядок. stdout/stderr читаються асинхронно паралельно — без deadlock.
/// </summary>
public sealed class ProcessRunner : IProcessRunner
{
    public async Task<ProcessResult> RunAsync(ProcessSpec spec, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(spec);

        var startInfo = new ProcessStartInfo(spec.FileName)
        {
            UseShellExecute = false,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
        };
        foreach (var argument in spec.Arguments)
        {
            startInfo.ArgumentList.Add(argument);
        }

        using var process = new System.Diagnostics.Process { StartInfo = startInfo };
        process.Start();

        var stdout = process.StandardOutput.ReadToEndAsync(CancellationToken.None);
        var stderr = process.StandardError.ReadToEndAsync(CancellationToken.None);

        using var timeout = new CancellationTokenSource(spec.Timeout);
        using var linked = CancellationTokenSource.CreateLinkedTokenSource(ct, timeout.Token);
        try
        {
            await WriteStandardInputAsync(process, spec.StandardInput, linked.Token).ConfigureAwait(false);
            await process.WaitForExitAsync(linked.Token).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            Kill(process);
            await process.WaitForExitAsync(CancellationToken.None).ConfigureAwait(false);
            ct.ThrowIfCancellationRequested();
            return new ProcessResult(-1, await stdout.ConfigureAwait(false), await stderr.ConfigureAwait(false), TimedOut: true);
        }

        return new ProcessResult(process.ExitCode, await stdout.ConfigureAwait(false), await stderr.ConfigureAwait(false), TimedOut: false);
    }

    private static async Task WriteStandardInputAsync(System.Diagnostics.Process process, string? input, CancellationToken ct)
    {
        try
        {
            if (input is not null)
            {
                await process.StandardInput.WriteAsync(input.AsMemory(), ct).ConfigureAwait(false);
                await process.StandardInput.FlushAsync(ct).ConfigureAwait(false);
            }

            process.StandardInput.Close();
        }
        catch (IOException)
        {
            // Процес завершився, не дочитавши stdin: результат визначить код виходу.
        }
    }

    private static void Kill(System.Diagnostics.Process process)
    {
        try
        {
            process.Kill(entireProcessTree: true);
        }
        catch (InvalidOperationException)
        {
            // Уже завершився.
        }
    }
}
