using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json;
using Scm.Core.Model;

namespace Scm.Agent;

internal sealed class Reporter : IDisposable
{
    private sealed record Settings(Uri Server, string Key);
    private readonly HttpClient client;
    private readonly X509Certificate2? authority;

    public static async Task ReportAsync(CancellationToken token)
    {
        var status = Inventory.Read();
        var directory = Path.Combine(AppContext.BaseDirectory, "config");
        var legacy = Path.Combine(directory, "agent.json");
        Settings? settings = null;
        string? caPath = null;
        if (!string.IsNullOrEmpty(status.Domain))
        {
            var host = "school-server." + status.Domain;
            try
            {
                // SMB authenticates the service with the computer account. Samba checks its file ACL.
                var key = await File.ReadAllTextAsync($@"\\{host}\scm-enroll\{status.ComputerName}.key", token).ConfigureAwait(false);
                settings = new Settings(new Uri($"https://{host}:8443"), key.Trim());
            }
            catch (Exception e) when ((e is IOException or UnauthorizedAccessException) && File.Exists(legacy))
            {
                // Previously registered machines keep reporting with their individual local credential.
            }
        }
        if (settings is null)
        {
            settings = JsonSerializer.Deserialize<Settings>(await File.ReadAllBytesAsync(legacy, token).ConfigureAwait(false))
                ?? throw new InvalidDataException("Missing agent settings.");
            caPath = Path.Combine(directory, "school-ca.cer");
        }
        using var reporter = new Reporter(settings, caPath);
        await reporter.SendAsync(status, token).ConfigureAwait(false);
    }

    private Reporter(Settings settings, string? caPath)
    {
        if (!settings.Server.IsAbsoluteUri || settings.Server.Scheme != Uri.UriSchemeHttps ||
            settings.Server.UserInfo.Length != 0 || settings.Key.Length != 48 || !settings.Key.All(Uri.IsHexDigit))
            throw new InvalidDataException("Invalid server address or device key.");

        var handler = new SocketsHttpHandler { AllowAutoRedirect = false };
        if (File.Exists(caPath))
        {
            authority = X509CertificateLoader.LoadCertificateFromFile(caPath);
            handler.SslOptions.CertificateChainPolicy = new X509ChainPolicy
            {
                TrustMode = X509ChainTrustMode.CustomRootTrust,
                CustomTrustStore = { authority },
                ApplicationPolicy = { new System.Security.Cryptography.Oid("1.3.6.1.5.5.7.3.1") },
                // The lab CA does not publish a revocation list.
                RevocationMode = X509RevocationMode.NoCheck
            };
        }
        client = new HttpClient(handler) { BaseAddress = settings.Server, Timeout = TimeSpan.FromSeconds(30) };
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", settings.Key);
    }

    private async Task SendAsync(AgentStatus status, CancellationToken token)
    {
        using var response = await client.PostAsJsonAsync("/agent/status", status, StatusJson.Default.AgentStatus, token).ConfigureAwait(false);
        response.EnsureSuccessStatusCode();
    }

    public void Dispose()
    {
        client.Dispose();
        authority?.Dispose();
    }
}
