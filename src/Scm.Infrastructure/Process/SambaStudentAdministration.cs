using System.Text.Json;
using Scm.Core.Model;
using Scm.Core.Ports;

namespace Scm.Infrastructure.Process;

public sealed class SambaStudentAdministration(IProcessRunner runner) : IStudentAdministration, IStudentFiles
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    public Task<TeacherSession> AuthenticateAsync(string login, string password, CancellationToken ct) =>
        CallAsync<TeacherSession>(new { op = "authenticate", login = new AccountName(login).Value, password }, ct);

    public Task<TeacherSession> SessionAsync(TeacherSession actor, CancellationToken ct) =>
        CallAsync<TeacherSession>(new { op = "session", actor }, ct);

    public async Task<IReadOnlyList<PupilAccount>> ListAsync(TeacherSession actor, CancellationToken ct) =>
        await CallAsync<PupilAccount[]>(new { op = "list", actor }, ct).ConfigureAwait(false);

    public Task<PupilCredentials> CreateAsync(TeacherSession actor, CreatePupil pupil, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(pupil);
        if (string.IsNullOrWhiteSpace(pupil.GivenName) || pupil.GivenName.Length > 64 ||
            string.IsNullOrWhiteSpace(pupil.Surname) || pupil.Surname.Length > 64 ||
            pupil.GivenName.Any(char.IsControl) || pupil.Surname.Any(char.IsControl))
        {
            throw new ArgumentException("Invalid pupil name.", nameof(pupil));
        }

        return CallAsync<PupilCredentials>(new { op = "create", actor, login = new AccountName(pupil.Login).Value,
            givenName = pupil.GivenName.Trim(), surname = pupil.Surname.Trim() }, ct);
    }

    public Task<PupilCredentials> ResetAsync(TeacherSession actor, string login, CancellationToken ct) =>
        CallAsync<PupilCredentials>(new { op = "reset", actor, login = new AccountName(login).Value }, ct);

    public async Task<IReadOnlyList<PupilFileEntry>> ListFilesAsync(TeacherSession actor, string login, string path, CancellationToken ct) =>
        await CallAsync<PupilFileEntry[]>(new { op = "files", actor, login = new AccountName(login).Value, path }, ct).ConfigureAwait(false);

    public Task<PupilDownload> DownloadAsync(TeacherSession actor, string login, string path, CancellationToken ct) =>
        CallAsync<PupilDownload>(new { op = "download", actor, login = new AccountName(login).Value, path }, ct);

    private async Task<T> CallAsync<T>(object request, CancellationToken ct)
    {
        var result = await runner.RunAsync(new ProcessSpec("/usr/bin/sudo", ["-n", "/usr/local/sbin/scm-directory"],
            JsonSerializer.Serialize(request, Json), TimeSpan.FromSeconds(30)), ct).ConfigureAwait(false);
        if (!result.Succeeded)
        {
            throw new DirectoryOperationException("unavailable");
        }

        try
        {
            using var document = JsonDocument.Parse(result.StandardOutput);
            if (document.RootElement.TryGetProperty("error", out var error))
            {
                throw new DirectoryOperationException(error.GetString() ?? "unavailable");
            }

            return document.RootElement.GetProperty("data").Deserialize<T>(Json)
                ?? throw new DirectoryOperationException("unavailable");
        }
        catch (JsonException)
        {
            throw new DirectoryOperationException("unavailable");
        }
    }
}
