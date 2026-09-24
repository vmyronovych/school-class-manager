using Scm.Core.Model;
using Scm.Core.Results;

namespace Scm.Core.Ports;

/// <summary>Зміни в AD через <c>sudo scm-user</c>.</summary>
public interface IAccountCommands
{
    Task<Result> CreateAsync(NewStudent s, string password, CancellationToken ct);

    Task<Result> SetPasswordAsync(Login login, string password, CancellationToken ct);

    Task<Result> UnlockAsync(Login login, CancellationToken ct);

    Task<Result> SetEnabledAsync(Login login, bool enabled, CancellationToken ct);

    /// <summary>Додати учня в групу класу; зі старих груп не виключає — переведення між класами немає.</summary>
    Task<Result> EnrollAsync(Login login, ClassCode cls, CancellationToken ct);
}
