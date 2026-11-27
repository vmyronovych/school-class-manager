using System.Diagnostics;
using System.Security.AccessControl;
using System.Security.Cryptography.X509Certificates;
using System.Security.Principal;
using System.ServiceProcess;
using System.Text;
using System.Text.Json;

namespace Scm.Agent;

internal static class Installer
{

    public static void Install(string server, string? caPath)
    {
        using var identity = WindowsIdentity.GetCurrent();
        if (!new WindowsPrincipal(identity).IsInRole(WindowsBuiltInRole.Administrator))
            throw new InvalidOperationException("Open the agent as administrator to install the Windows service.");
        if (!Uri.TryCreate(server, UriKind.Absolute, out var uri) || uri.Scheme != Uri.UriSchemeHttps ||
            uri.PathAndQuery != "/" || uri.UserInfo.Length != 0 || uri.Fragment.Length != 0)
            throw new ArgumentException("Enter an HTTPS server address without a path.");
        var executable = Environment.ProcessPath ?? throw new InvalidOperationException("Cannot locate the agent.");
        if (!string.Equals(Path.GetFileName(executable), "Scm.Agent.exe", StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Install using the published Scm.Agent.exe.");
        byte[]? ca = null;
        if (caPath != null)
        {
            using var certificate = X509CertificateLoader.LoadCertificateFromFile(caPath);
            if (!certificate.Extensions.OfType<X509BasicConstraintsExtension>().Any(ext => ext.CertificateAuthority))
                throw new InvalidDataException("The supplied certificate is not a certificate authority.");
            ca = certificate.Export(X509ContentType.Cert);
        }

        Console.WriteLine($"Installing on {Environment.MachineName} for {uri.Authority}");
        Console.Write("Paste the report key for this computer and press Enter: ");
        var key = ReadKey();
        if (key.Length != 48 || !key.All(Uri.IsHexDigit))
            throw new InvalidDataException("Expected a 48-character hexadecimal report key.");

        var directory = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "School Class Manager", "Agent");
        Directory.CreateDirectory(directory);
        var target = Path.Combine(directory, "Scm.Agent.exe");
        var config = new DirectoryInfo(Path.Combine(directory, "config"));
        using var service = new ServiceController(AgentService.Name);
        // Query the service manager before changing an existing installation.
        using var query = RunSc("query", AgentService.Name);
        if (query.ExitCode == 0)
        {
            if (service.Status != ServiceControllerStatus.Stopped)
            {
                if (service.Status != ServiceControllerStatus.StopPending) service.Stop();
                service.WaitForStatus(ServiceControllerStatus.Stopped, TimeSpan.FromSeconds(30));
            }
        }
        else if (query.ExitCode != 1060) throw new InvalidOperationException($"Service lookup failed ({query.ExitCode}).");

        if (!string.Equals(executable, target, StringComparison.OrdinalIgnoreCase))
        {
            File.Copy(executable, target + ".new", true);
            File.Move(target + ".new", target, true);
        }
        // A stopped, demand-start service gets its identity before private configuration is written.
        if (query.ExitCode != 0)
            ConfigureService("create", AgentService.Name, "binPath=", $"\"{target}\" service", "start=", "demand",
                "obj=", @"NT AUTHORITY\LocalService", "DisplayName=", "School Class Manager Agent");
        ConfigureService("sidtype", AgentService.Name, "unrestricted");

        var permissions = new DirectorySecurity();
        permissions.SetAccessRuleProtection(true, false);
        var admins = new SecurityIdentifier(WellKnownSidType.BuiltinAdministratorsSid, null);
        permissions.SetOwner(admins);
        AddPermission(permissions, admins, FileSystemRights.FullControl);
        AddPermission(permissions, new SecurityIdentifier(WellKnownSidType.LocalSystemSid, null), FileSystemRights.FullControl);
        AddPermission(permissions, new NTAccount(@"NT SERVICE", AgentService.Name), FileSystemRights.ReadAndExecute);
        if (config.Exists) config.SetAccessControl(permissions);
        else config.Create(permissions);

        var certFile = Path.Combine(config.FullName, "school-ca.cer");
        if (ca != null) Replace(certFile, ca);
        else File.Delete(certFile);
        Replace(Path.Combine(config.FullName, "agent.json"), JsonSerializer.SerializeToUtf8Bytes(new { Server = uri, Key = key }));
        if (!EventLog.SourceExists(AgentService.Name)) EventLog.CreateEventSource(AgentService.Name, "Application");
        ConfigureService("config", AgentService.Name, "start=", "auto");
        service.Start();
        service.WaitForStatus(ServiceControllerStatus.Running, TimeSpan.FromSeconds(30));
        Console.WriteLine("ScmAgent is running. Check the last report time in the panel.");
    }

    private static string ReadKey()
    {
        if (Console.IsInputRedirected) return Console.ReadLine()?.Trim() ?? string.Empty;
        var input = new StringBuilder();
        while (true)
        {
            var key = Console.ReadKey(true);
            if (key.Key == ConsoleKey.Enter) break;
            if (key.Key == ConsoleKey.Backspace && input.Length > 0) input.Length--;
            else if (!char.IsControl(key.KeyChar)) input.Append(key.KeyChar);
        }
        Console.WriteLine();
        return input.ToString().Trim();
    }

    private static void AddPermission(DirectorySecurity acl, IdentityReference account, FileSystemRights rights) =>
        acl.AddAccessRule(new FileSystemAccessRule(account, rights, InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit,
            PropagationFlags.None, AccessControlType.Allow));

    private static void Replace(string path, byte[] contents)
    {
        File.WriteAllBytes(path + ".new", contents);
        File.Move(path + ".new", path, true);
    }

    private static Process RunSc(params string[] args)
    {
        var start = new ProcessStartInfo(Path.Combine(Environment.SystemDirectory, "sc.exe")) { UseShellExecute = false };
        foreach (var arg in args) start.ArgumentList.Add(arg);
        var process = Process.Start(start) ?? throw new InvalidOperationException("Cannot open the service manager.");
        process.WaitForExit();
        return process;
    }

    private static void ConfigureService(params string[] args)
    {
        using var process = RunSc(args);
        if (process.ExitCode != 0) throw new InvalidOperationException($"Service configuration failed ({process.ExitCode}).");
    }
}
