using System.ServiceProcess;
using System.Text.Json;
using Scm.Agent;

try
{
    switch (args)
    {
        case ["install", var server, var caPath]:
            Installer.Install(server, caPath);
            break;
        case ["install", var server]:
            Installer.Install(server, null);
            break;
        case ["service"]:
            using (var service = new AgentService()) ServiceBase.Run(service);
            break;
        case ["status"]:
            Console.WriteLine(JsonSerializer.Serialize(Inventory.Read(), StatusJson.Default.AgentStatus));
            break;
        case ["report"]:
            await Reporter.ReportAsync(CancellationToken.None).ConfigureAwait(false);
            Console.WriteLine("Workstation report accepted.");
            break;
        default:
            Console.Error.WriteLine("Usage: Scm.Agent.exe install https://server[:port] [ca.cer] | status | report | service");
            return 2;
    }
    return 0;
}
catch (Exception e)
{
    Console.Error.WriteLine(e.Message);
    return 1;
}
[System.Text.Json.Serialization.JsonSourceGenerationOptions(JsonSerializerDefaults.Web)]
[System.Text.Json.Serialization.JsonSerializable(typeof(Scm.Core.Model.AgentStatus))]
internal sealed partial class StatusJson : System.Text.Json.Serialization.JsonSerializerContext;
