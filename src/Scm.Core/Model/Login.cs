using System.Text.RegularExpressions;

namespace Scm.Core.Model;

/// <summary>
/// Доменний логін (sAMAccountName), не довше 20 символів.
/// Учень: <c>прізвище.ім'я.рік_народження</c> — <c>ivanenko.petro.2011</c>, <c>kovalenko.a.2011</c>,
/// при ручному розв'язанні збігу — з літерою перед роком: <c>ivanenko.p.o.2011</c>.
/// Вчитель: <c>viktor.admin</c>, <c>v.prizvyshche</c> — без року, тож із логіном учня не плутається.
/// Ті самі регулярні вирази, що й в обгортці <c>pi/sbin/scm-user</c>.
/// </summary>
public sealed partial record Login
{
    public const int MaxLength = 20;

    public Login(string value)
    {
        ArgumentNullException.ThrowIfNull(value);
        if (value.Length > MaxLength || (!StudentPattern().IsMatch(value) && !TeacherPattern().IsMatch(value)))
        {
            throw new ArgumentException($"Невалідний логін: '{value}'.", nameof(value));
        }

        Value = value;
    }

    public string Value { get; }

    public bool IsStudent => StudentPattern().IsMatch(Value);

    public override string ToString() => Value;

    [GeneratedRegex(@"^[a-z]+(-[a-z]+)?\.[a-z]+(-[a-z]+)?(\.[a-z])?\.(19|20)[0-9]{2}$", RegexOptions.CultureInvariant)]
    private static partial Regex StudentPattern();

    [GeneratedRegex(@"^[a-z]+\.[a-z]+(\.[a-z]+)?$", RegexOptions.CultureInvariant)]
    private static partial Regex TeacherPattern();
}
