namespace Scm.Core.Model;

public sealed record FileEntry(string Name, long SizeBytes, DateTimeOffset ModifiedAt, string? Owner);
