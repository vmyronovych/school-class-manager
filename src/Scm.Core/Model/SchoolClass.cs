namespace Scm.Core.Model;

/// <summary>Клас: <c>4a</c> / «4-А». Група в AD — <c>uchni-&lt;код&gt;</c>.</summary>
public sealed record SchoolClass(ClassCode Code, string DisplayName, int StudentCount);
