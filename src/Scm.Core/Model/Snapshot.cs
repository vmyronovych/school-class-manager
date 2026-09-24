namespace Scm.Core.Model;

/// <summary>Знімок Btrfs: <c>.snapshots/@GMT-…</c>.</summary>
public sealed record Snapshot(DateTimeOffset TakenAt, string Path);
