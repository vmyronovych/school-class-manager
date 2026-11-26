using System.Security.Claims;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Scm.Core.Ports;

namespace Scm.Api.Endpoints;

public sealed record LoginRequest(string Login, string Password);
public sealed record CsrfResponse(string Token);
public sealed record ApiError(string Code);

public static class PupilEndpoints
{
    public static void MapPupils(this WebApplication app)
    {
        var api = app.MapGroup("/api");
        api.MapGet("/auth/csrf", (HttpContext context, IAntiforgery csrf) =>
            new CsrfResponse(csrf.GetAndStoreTokens(context).RequestToken!)).AllowAnonymous();

        api.MapPost("/auth/login", async (LoginRequest request, HttpContext context,
            IStudentAdministration directory, CancellationToken ct) =>
        {
            if (string.IsNullOrWhiteSpace(request.Login) || string.IsNullOrEmpty(request.Password) || request.Password.Length > 256)
            {
                throw new DirectoryOperationException("credentials");
            }

            var teacher = await directory.AuthenticateAsync(request.Login, request.Password, ct);
            var identity = new ClaimsIdentity(new[] {
                new Claim(ClaimTypes.NameIdentifier, teacher.Sid),
                new Claim(ClaimTypes.Name, teacher.Login),
                new Claim(ClaimTypes.Role, teacher.Role),
                new Claim("displayName", teacher.DisplayName),
            }, CookieAuthenticationDefaults.AuthenticationScheme);
            await context.SignInAsync(CookieAuthenticationDefaults.AuthenticationScheme, new ClaimsPrincipal(identity));
            return teacher;
        }).AllowAnonymous().RequireRateLimiting("login").Produces<TeacherSession>();

        api.MapPost("/auth/logout", async (HttpContext context) =>
        {
            await context.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
            return Results.NoContent();
        }).RequireAuthorization("Teacher");
        api.MapGet("/me", (HttpContext context, IStudentAdministration directory, CancellationToken ct) =>
            directory.SessionAsync(Actor(context.User), ct)).RequireAuthorization("Teacher").Produces<TeacherSession>();
        api.MapGet("/students", (HttpContext context, IStudentAdministration directory, CancellationToken ct) =>
            directory.ListAsync(Actor(context.User), ct)).RequireAuthorization("Teacher").Produces<IReadOnlyList<PupilAccount>>();
        api.MapPost("/students", (CreatePupil pupil, HttpContext context,
            IStudentAdministration directory, CancellationToken ct) =>
            directory.CreateAsync(Actor(context.User), pupil, ct)).RequireAuthorization("Teacher").Produces<PupilCredentials>();
        api.MapPost("/students/{login}/reset-password", (string login, HttpContext context,
            IStudentAdministration directory, CancellationToken ct) =>
            directory.ResetAsync(Actor(context.User), login, ct)).RequireAuthorization("Teacher").Produces<PupilCredentials>();
    }

    internal static TeacherSession Actor(ClaimsPrincipal principal) => new(
        principal.Identity!.Name!, principal.FindFirstValue("displayName")!,
        principal.FindFirstValue(ClaimTypes.Role)!, principal.FindFirstValue(ClaimTypes.NameIdentifier)!);
}
