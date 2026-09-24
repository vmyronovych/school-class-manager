namespace Scm.Core.Model;

public sealed record Student(
    Login Login,
    string Surname,
    string GivenName,
    ClassCode ClassCode,
    StudentStatus Status,
    DateTimeOffset? LastLogon,
    string? LastLogonPc,
    long? HomeSizeBytes,
    DateTimeOffset? PasswordChangedAt);
