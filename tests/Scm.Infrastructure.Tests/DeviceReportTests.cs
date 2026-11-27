using System.Text;
using Scm.Core.Model;
using Scm.Infrastructure;

namespace Scm.Infrastructure.Tests;

public sealed class DeviceReportTests
{
    [Fact]
    public void OnlyTheEnrolledMachineKeyIsAcceptedAndRemovalRevokesIt()
    {
        var root = Directory.CreateTempSubdirectory();
        try
        {
            var keys = root.CreateSubdirectory("keys");
            var path = Path.Combine(keys.FullName, "PC-A.key");
            var reports = new DeviceReports(Path.Combine(root.FullName, "reports"), keys.FullName);
            var status = new AgentStatus("pc-a", "campus.example", "Windows", "1", 3, 2, false, "0.2.0");
            var key = new string('A', 48);
            File.WriteAllText(path, key, Encoding.ASCII);
            reports.Receive(status, new string('B', 48)).Should().BeFalse();
            reports.Receive(status with { ComputerName = "PC-B" }, key).Should().BeFalse();
            reports.Receive(status, key).Should().BeTrue();
            reports.List().Single().Managed.Should().BeTrue();
            reports.Register("PC-A", true).Should().BeNull();
            File.Delete(path);
            reports.Receive(status, key).Should().BeFalse();
        }
        finally { root.Delete(true); }
    }
}
