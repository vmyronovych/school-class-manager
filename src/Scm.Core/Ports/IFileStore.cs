using Scm.Core.Model;

namespace Scm.Core.Ports;

/// <summary>Файли на шарах <c>/srv/data</c> і знімки.</summary>
public interface IFileStore
{
    Task<IReadOnlyList<FileEntry>> ListAsync(StorePath path, CancellationToken ct);

    Task SaveAsync(StorePath dir, string fileName, Stream content, Owner owner, CancellationToken ct);

    Task<Stream> OpenReadAsync(StorePath file, CancellationToken ct);

    Task<IReadOnlyList<Snapshot>> GetSnapshotsAsync(Share share, CancellationToken ct);

    Task RestoreAsync(Login login, Snapshot snap, string relPath, CancellationToken ct);
}
