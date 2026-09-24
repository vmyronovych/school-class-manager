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

    Task<Result> MoveAsync(Login login, ClassCode fromClass, ClassCode toClass, CancellationToken ct);
}
