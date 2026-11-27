using System.Management;
using System.Runtime.InteropServices;
using Scm.Core.Model;
using Windows.System.Profile;

namespace Scm.Agent;

internal static class Inventory
{
    public static AgentStatus Read()
    {
        using var osQuery = new ManagementObjectSearcher("SELECT Caption, BuildNumber, SystemDrive FROM Win32_OperatingSystem");
        using var systems = osQuery.Get();
        using var os = systems.Cast<ManagementObject>().First();
        using var domainQuery = new ManagementObjectSearcher("SELECT Domain, PartOfDomain FROM Win32_ComputerSystem");
        using var computers = domainQuery.Get();
        using var computer = computers.Cast<ManagementObject>().First();
        using var profilesQuery = new ManagementObjectSearcher("SELECT SID FROM Win32_UserProfile WHERE Special = FALSE");
        using var profiles = profilesQuery.Get();
        var drive = new DriveInfo((string)os["SystemDrive"]);
        bool? sharedPc;
        try { sharedPc = SharedModeSettings.IsEnabled; }
        catch (Exception e) when (e is COMException or UnauthorizedAccessException or TypeLoadException)
        {
            sharedPc = null;
        }

        return new(Environment.MachineName, (bool)computer["PartOfDomain"] ? (string)computer["Domain"] : null,
            (string)os["Caption"], (string)os["BuildNumber"], Math.Round(drive.TotalFreeSpace / 1073741824m, 2),
            profiles.Count, sharedPc, typeof(Inventory).Assembly.GetName().Version!.ToString(3));
    }
}
