using Scm.Core.Model;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Scm.Infrastructure;

public sealed record DeviceView(string ComputerName, DateTimeOffset? ReceivedAt, AgentStatus? Status, bool Managed = false);

public sealed partial class DeviceReports(string directory, string? enrollmentDirectory = null)
{
    private sealed record Entry(string? KeyHash, DeviceView Device);
    private readonly object gate = new();

    [GeneratedRegex(@"\A[A-Za-z0-9](?:[A-Za-z0-9-]{0,13}[A-Za-z0-9])?\z", RegexOptions.CultureInvariant)]
    private static partial Regex ComputerNamePattern();

    private static string Normalize(string name) => name is not null && ComputerNamePattern().IsMatch(name)
        ? name.ToUpperInvariant() : throw new ArgumentException("Invalid computer name.", nameof(name));

    private string FileFor(string name) => Path.Combine(directory, Normalize(name) + ".json");
    private string? ManagedKeyPath(string name) => enrollmentDirectory is null ? null :
        Path.Combine(enrollmentDirectory, Normalize(name) + ".key");

    private static Entry Read(string file) => JsonSerializer.Deserialize<Entry>(File.ReadAllBytes(file))!;
    private void Save(string path, Entry entry)
    {
        Directory.CreateDirectory(directory);
        var temp = path + ".tmp";
        try
        {
            File.WriteAllBytes(temp, JsonSerializer.SerializeToUtf8Bytes(entry));
            File.Move(temp, path, true);
        }
        finally { File.Delete(temp); }
    }

    public IReadOnlyList<DeviceView> List()
    {
        lock (gate)
        {
            return Directory.Exists(directory)
                ? Directory.GetFiles(directory, "*.json").Order(StringComparer.Ordinal).Select(p => Read(p).Device).ToArray()
                : [];
        }
    }

    public string? Register(string name, bool replace)
    {
        name = Normalize(name);
        var path = FileFor(name);
        lock (gate)
        {
            if (File.Exists(ManagedKeyPath(name)) || (File.Exists(path) && (!replace || Read(path).Device.Managed))) return null;
            var device = File.Exists(path) ? Read(path).Device : new DeviceView(name, null, null);
            var key = Convert.ToHexString(RandomNumberGenerator.GetBytes(24));
            Save(path, new Entry(Convert.ToHexString(SHA256.HashData(Encoding.ASCII.GetBytes(key))), device));
            return key;
        }
    }

    public bool Receive(AgentStatus status, string key)
    {
        var path = FileFor(status.ComputerName);
        lock (gate)
        {
            if (key.Length != 48) return false;
            var managedKey = ManagedKeyPath(status.ComputerName);
            var managed = File.Exists(managedKey);
            var entry = File.Exists(path) ? Read(path) : null;
            byte[] expected;
            if (managed)
                expected = SHA256.HashData(File.ReadAllBytes(managedKey!));
            else if (entry?.KeyHash is { } hash && !entry.Device.Managed)
                expected = Convert.FromHexString(hash);
            else return false;
            if (!CryptographicOperations.FixedTimeEquals(expected, SHA256.HashData(Encoding.ASCII.GetBytes(key)))) return false;
            if (status.SystemDriveFreeGiB is null or < 0 || status.NonSystemProfileCount is null or < 0
                || string.IsNullOrWhiteSpace(status.WindowsBuild) || status.WindowsBuild.Length > 32
                || string.IsNullOrWhiteSpace(status.WindowsEdition) || status.WindowsEdition.Length > 128
                || status.Domain?.Length > 253 || status.AgentVersion?.Length > 32) throw new ArgumentException("Invalid status.", nameof(status));
            Save(path, new Entry(managed ? null : entry!.KeyHash, new DeviceView(Normalize(status.ComputerName), DateTimeOffset.UtcNow, status, managed)));
            return true;
        }
    }
}
