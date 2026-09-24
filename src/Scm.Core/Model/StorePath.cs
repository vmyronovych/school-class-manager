namespace Scm.Core.Model;

/// <summary>
/// Відносний шлях усередині шари, розділювач — <c>/</c>. Порожній шлях, абсолютний шлях,
/// <c>\</c>, керівні символи, порожні сегменти, <c>.</c> і <c>..</c> відхиляються, тож шлях
/// ніколи не виходить за корінь шари. Друга лінія захисту — PathGuard в Infrastructure
/// (<c>Path.GetFullPath</c> + <c>StartsWith</c>) проти реального кореня.
/// </summary>
public sealed record StorePath
{
    public StorePath(Share share, string relative)
    {
        ArgumentNullException.ThrowIfNull(relative);
        if (!Enum.IsDefined(share))
        {
            throw new ArgumentOutOfRangeException(nameof(share), share, "Невідома шара.");
        }

        if (!IsValidRelative(relative))
        {
            throw new ArgumentException($"Невалідний шлях: '{relative}'.", nameof(relative));
        }

        Share = share;
        Relative = relative;
    }

    public Share Share { get; }

    public string Relative { get; }

    public override string ToString() => $"{Share}:{Relative}";

    private static bool IsValidRelative(string relative)
    {
        if (relative.Length == 0 || relative[0] == '/' || relative.Contains('\\', StringComparison.Ordinal))
        {
            return false;
        }

        if (relative.Any(char.IsControl))
        {
            return false;
        }

        return relative.Split('/').All(segment =>
            segment.Length > 0 && segment != "." && segment != ".." && !string.IsNullOrWhiteSpace(segment));
    }
}
