using Scm.Core.Ports;

namespace Scm.Api.Endpoints;

public static class PupilFileEndpoints
{
    public static void MapPupilFiles(this WebApplication app)
    {
        var api = app.MapGroup("/api/students/{login}").RequireAuthorization("Teacher");
        api.MapGet("/files", (string login, string? path, HttpContext context, IStudentFiles files, CancellationToken ct) =>
            files.ListFilesAsync(PupilEndpoints.Actor(context.User), login, path ?? "", ct))
            .Produces<IReadOnlyList<PupilFileEntry>>();
        api.MapGet("/download", async (string login, string path, HttpContext context, IStudentFiles files, CancellationToken ct) =>
        {
            var download = await files.DownloadAsync(PupilEndpoints.Actor(context.User), login, path, ct);
            return Results.File(download.Content, "application/octet-stream", download.Name);
        }).Produces(StatusCodes.Status200OK, contentType: "application/octet-stream");
    }
}
