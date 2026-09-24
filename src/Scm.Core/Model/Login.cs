using System.Text.RegularExpressions;

namespace Scm.Core.Model;

/// <summary>
/// Доменний логін. Учень: <c>4a.ivanenko</c> або <c>4a.ivanenko.p</c>; вчитель: <c>viktor.admin</c>.
/// Ті самі регулярні вирази, що й в обгортці <c>pi/sbin/scm-user</c>.
/// </summary>
public sealed partial record Login
{
    public Login(string value)
    {
        ArgumentNullException.ThrowIfNull(value);
        if (!StudentPattern().IsMatch(value) && !TeacherPattern().IsMatch(value))
        {
            throw new ArgumentException($"Невалідний логін: '{value}'.", nameof(value));
        }

        Value = value;
    }

    public string Value { get; }

    public bool IsStudent => StudentPattern().IsMatch(Value);

    public override string ToString() => Value;

    [GeneratedRegex(@"^[0-9]{1,2}[a-z]\.[a-z]+(\.[a-z]+)?$", RegexOptions.CultureInvariant)]
    private static partial Regex StudentPattern();

    [GeneratedRegex(@"^[a-z]+\.[a-z]+(\.[a-z]+)?$", RegexOptions.CultureInvariant)]
    private static partial Regex TeacherPattern();
}
