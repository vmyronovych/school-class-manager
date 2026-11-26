using System.Text.RegularExpressions;

namespace Scm.Core.Model;

/// <summary>An AD account name; student/teacher roles come from groups, not spelling.</summary>
public sealed partial record AccountName
{
    public AccountName(string value)
    {
        ArgumentNullException.ThrowIfNull(value);
        Value = value.Trim().ToLowerInvariant();
        if (!Pattern().IsMatch(Value))
        {
            throw new ArgumentException("Invalid account name.", nameof(value));
        }
    }

    public string Value { get; }

    [GeneratedRegex(@"\A[a-z][a-z0-9.-]{0,63}\z", RegexOptions.CultureInvariant)]
    private static partial Regex Pattern();
}
