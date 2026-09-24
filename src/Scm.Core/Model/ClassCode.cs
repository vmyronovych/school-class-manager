using System.Globalization;
using System.Text.RegularExpressions;

namespace Scm.Core.Model;

/// <summary>
/// Код класу: <c>&lt;рік&gt;-&lt;клас&gt;</c>, напр. <c>2025-4a</c> — 4-А у 2025/26 навчальному році.
/// Група в AD — <c>uchni-2025-4a</c>, папка — <c>class/2025-4a</c>. Наступного року той самий клас — <c>2026-5a</c>.
/// </summary>
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

    /// <summary>Рік початку навчального року: 2025 для 2025/26.</summary>
    public int SchoolYear => int.Parse(Value.AsSpan(0, 4), CultureInfo.InvariantCulture);

    public override string ToString() => Value;

    [GeneratedRegex(@"^20[0-9]{2}-[0-9]{1,2}[a-z]$", RegexOptions.CultureInvariant)]
    private static partial Regex Pattern();
}
