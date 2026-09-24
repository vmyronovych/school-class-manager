namespace Scm.Core.Results;

/// <summary>Помилка домену: машинний код + людський текст (і stderr обгортки для «Деталі»).</summary>
public sealed record DomainError(string Code, string Message, string? Details = null);
