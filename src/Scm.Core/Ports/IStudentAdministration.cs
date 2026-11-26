namespace Scm.Core.Ports;

public sealed record TeacherSession(string Login, string DisplayName, string Role, string Sid);
public sealed record PupilAccount(string Login, string DisplayName, bool Enabled, string? HomeDirectory);
public sealed record PupilCredentials(string Login, string Password);
public sealed record CreatePupil(string Login, string GivenName, string Surname);

public interface IStudentAdministration
{
    Task<TeacherSession> AuthenticateAsync(string login, string password, CancellationToken ct);
    Task<TeacherSession> SessionAsync(TeacherSession actor, CancellationToken ct);
    Task<IReadOnlyList<PupilAccount>> ListAsync(TeacherSession actor, CancellationToken ct);
    Task<PupilCredentials> CreateAsync(TeacherSession actor, CreatePupil pupil, CancellationToken ct);
    Task<PupilCredentials> ResetAsync(TeacherSession actor, string login, CancellationToken ct);
}

public sealed class DirectoryOperationException(string code) : Exception("Directory operation failed.")
{
    public string Code { get; } = code;
}
