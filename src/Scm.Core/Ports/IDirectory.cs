using Scm.Core.Model;

namespace Scm.Core.Ports;

/// <summary>Читання каталогу AD (LDAP) і вхід вчителя.</summary>
public interface IDirectory
{
    Task<AuthResult> AuthenticateAsync(string login, string password, CancellationToken ct);

    Task<IReadOnlyList<Student>> GetStudentsAsync(ClassCode? cls, CancellationToken ct);

    Task<Student?> GetStudentAsync(Login login, CancellationToken ct);

    Task<IReadOnlyList<SchoolClass>> GetClassesAsync(CancellationToken ct);
}
