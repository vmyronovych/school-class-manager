using Scm.Core.Model;
using Scm.Core.Ports;
using Scm.Core.Results;

namespace Scm.Infrastructure.Process;

/// <summary>
/// <see cref="IAccountCommands"/> через <c>sudo scm-user</c>. Пароль іде тільки в stdin з кінцевим <c>\n</c>
/// (обгортка читає його <c>read -r</c>). Логін вчителя отримує <c>--teacher</c>; чи має викликач
/// право на це (роль Admin), перевіряє use-case, а обгортка ще раз звіряє групу <c>vchyteli</c>.
/// </summary>
public sealed class SudoAccountCommands(SudoRunner sudo) : IAccountCommands
{
    public Task<Result> CreateAsync(NewStudent s, string password, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(s);
        RequireStudent(s.Login);
        RequireName(s.Surname, nameof(s.Surname));
        RequireName(s.GivenName, nameof(s.GivenName));

        return RunAsync(
            ["create", s.Login.Value, "--class", s.ClassCode.Value, "--given-name", s.GivenName, "--surname", s.Surname],
            PasswordInput(password),
            ct);
    }

    public Task<Result> SetPasswordAsync(Login login, string password, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(login);
        return RunAsync(WithTeacherFlag(["setpassword", login.Value], login), PasswordInput(password), ct);
    }

    public Task<Result> UnlockAsync(Login login, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(login);
        return RunAsync(WithTeacherFlag(["unlock", login.Value], login), null, ct);
    }

    public Task<Result> SetEnabledAsync(Login login, bool enabled, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(login);
        return RunAsync(WithTeacherFlag([enabled ? "enable" : "disable", login.Value], login), null, ct);
    }

    public Task<Result> EnrollAsync(Login login, ClassCode cls, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(login);
        ArgumentNullException.ThrowIfNull(cls);
        RequireStudent(login);

        return RunAsync(["enroll", login.Value, cls.Value], null, ct);
    }

    private async Task<Result> RunAsync(string[] arguments, string? input, CancellationToken ct)
    {
        var result = await sudo.RunAsync(SudoProgram.ScmUser, arguments, input, SudoRunner.DefaultTimeout, ct)
            .ConfigureAwait(false);

        if (result.TimedOut)
        {
            return Result.Failure(new DomainError("scm-user.timeout", $"scm-user {arguments[0]}: перевищено час очікування."));
        }

        return result.Succeeded
            ? Result.Success()
            : Result.Failure(new DomainError(
                "scm-user.failed",
                $"scm-user {arguments[0]} завершився з кодом {result.ExitCode}.",
                result.StandardError.Trim()));
    }

    private static string[] WithTeacherFlag(string[] arguments, Login login) =>
        login.IsStudent ? arguments : [.. arguments, "--teacher"];

    private static string PasswordInput(string password)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(password);
        if (password.Any(char.IsControl))
        {
            // \n обрізав би пароль у read -r обгортки.
            throw new ArgumentException("Пароль не може містити керівних символів.", nameof(password));
        }

        return password + "\n";
    }

    private static void RequireStudent(Login login)
    {
        if (!login.IsStudent)
        {
            throw new ArgumentException($"Операція дозволена лише для учня, а не '{login}'.", nameof(login));
        }
    }

    private static void RequireName(string value, string paramName)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(value, paramName);
        if (value.Any(char.IsControl))
        {
            throw new ArgumentException("Ім'я не може містити керівних символів.", paramName);
        }
    }
}
