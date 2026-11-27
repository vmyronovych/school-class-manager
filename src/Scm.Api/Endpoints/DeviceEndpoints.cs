using Scm.Core.Model;
using Scm.Core.Ports;
using Scm.Infrastructure;

namespace Scm.Api.Endpoints;

public sealed record RegisterDevice(string ComputerName, bool Replace);
public sealed record ReportKey(string Key);

public static class DeviceEndpoints
{
    public static void MapDevices(this WebApplication app)
    {
        app.MapGet("/api/devices", async (HttpContext ctx, IStudentAdministration directory, DeviceReports reports, CancellationToken ct) =>
        {
            await directory.SessionAsync(PupilEndpoints.Actor(ctx.User), ct);
            return reports.List();
        }).RequireAuthorization("Teacher");
        app.MapPost("/api/devices", async (RegisterDevice request, HttpContext ctx, IStudentAdministration directory, DeviceReports reports, CancellationToken ct) =>
        {
            var teacher = await directory.SessionAsync(PupilEndpoints.Actor(ctx.User), ct);
            if (teacher.Role != "Admin") return Results.Forbid();
            var key = reports.Register(request.ComputerName, request.Replace);
            return key is null ? Results.Conflict(new ApiError("exists")) : Results.Ok(new ReportKey(key));
        }).RequireAuthorization("Teacher").Produces<ReportKey>();
        // Device credentials only; browser session cookies grant no reporting privileges.
        app.MapPost("/agent/status", (AgentStatus status, HttpContext ctx, DeviceReports reports) =>
        {
            if (!ctx.Request.IsHttps) return Results.BadRequest();
            var auth = ctx.Request.Headers.Authorization.ToString();
            return auth.StartsWith("Bearer ", StringComparison.Ordinal) && reports.Receive(status, auth[7..])
                ? Results.NoContent() : Results.Unauthorized();
        }).AllowAnonymous();
    }
}
