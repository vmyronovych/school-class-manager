using System.Diagnostics;
using System.ServiceProcess;

namespace Scm.Agent;

internal sealed class AgentService : ServiceBase
{
    internal const string Name = "ScmAgent";
    private readonly CancellationTokenSource stopping = new();
    private Task? worker;

    public AgentService() => ServiceName = Name;

    protected override void OnStart(string[] args)
    {
        worker = Task.Run(() => RunAsync(stopping.Token));
    }

    private async Task RunAsync(CancellationToken token)
    {
        while (!token.IsCancellationRequested)
        {
            try { await Reporter.ReportAsync(token).ConfigureAwait(false); }
            catch (OperationCanceledException) when (token.IsCancellationRequested) { return; }
            catch (Exception e)
            {
                EventLog.WriteEntry("Workstation report failed: " + e.Message, EventLogEntryType.Warning);
            }
            await Task.Delay(TimeSpan.FromMinutes(5), token).ConfigureAwait(false);
        }
    }

    protected override void OnStop()
    {
        stopping.Cancel();
        try { worker?.WaitAsync(TimeSpan.FromSeconds(10)).GetAwaiter().GetResult(); }
        catch (OperationCanceledException) when (stopping.IsCancellationRequested) { }
        catch (System.TimeoutException) { }
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing) stopping.Dispose();
        base.Dispose(disposing);
    }
}
