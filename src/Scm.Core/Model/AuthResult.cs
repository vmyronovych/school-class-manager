namespace Scm.Core.Model;

public enum AuthOutcome
{
    Success,
    InvalidCredentials,
    NotATeacher,
}

public sealed record AuthResult(AuthOutcome Outcome, Login? Login = null, string? DisplayName = null, Role? Role = null);
