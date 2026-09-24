namespace Scm.Core.Results;

public class Result
{
    private protected Result(DomainError? error) => Error = error;

    public DomainError? Error { get; }

    public bool IsSuccess => Error is null;

    public static Result Success() => new(null);

    public static Result<T> Success<T>(T value) => new(value, null);

    public static Result Failure(DomainError error)
    {
        ArgumentNullException.ThrowIfNull(error);
        return new(error);
    }

    public static Result<T> Failure<T>(DomainError error)
    {
        ArgumentNullException.ThrowIfNull(error);
        return new(default, error);
    }
}

public sealed class Result<T> : Result
{
    private readonly T? _value;

    internal Result(T? value, DomainError? error)
        : base(error) => _value = value;

    public T Value => IsSuccess ? _value! : throw new InvalidOperationException("Результат містить помилку.");
}
