namespace Scm.Core.Ports;

public sealed record PupilFileEntry(string Name, bool Directory, long? Size, DateTimeOffset Modified);
public sealed record PupilDownload(string Name, byte[] Content);

public interface IStudentFiles
{
    Task<IReadOnlyList<PupilFileEntry>> ListFilesAsync(TeacherSession actor, string login, string path, CancellationToken ct);
    Task<PupilDownload> DownloadAsync(TeacherSession actor, string login, string path, CancellationToken ct);
}
