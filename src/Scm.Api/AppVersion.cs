using System.Reflection;

namespace Scm.Api;

/// <summary><c>Version</c> з Directory.Build.props, без суфікса <c>+&lt;commit&gt;</c>.</summary>
public static class AppVersion
{
    public static string Current { get; } = Read();

    private static string Read()
    {
        var informational = typeof(AppVersion).Assembly
            .GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion ?? "0.0.0";
        var plus = informational.IndexOf('+', StringComparison.Ordinal);
        return plus < 0 ? informational : informational[..plus];
    }
}
