using System.Text.RegularExpressions;

namespace Scm.Core.Model;

/// <summary>Код класу: <c>4a</c>, <c>11b</c>. Група в AD — <c>uchni-&lt;код&gt;</c>.</summary>
public sealed partial record ClassCode
{
    public ClassCode(string value)
    {
        ArgumentNullException.ThrowIfNull(value);
        if (!Pattern().IsMatch(value))
        {
            throw new ArgumentException($"Невалідний код класу: '{value}'.", nameof(value));
        }

        Value = value;
    }

    public string Value { get; }

    public override string ToString() => Value;

    [GeneratedRegex(@"^[0-9]{1,2}[a-z]$", RegexOptions.CultureInvariant)]
    private static partial Regex Pattern();
}
