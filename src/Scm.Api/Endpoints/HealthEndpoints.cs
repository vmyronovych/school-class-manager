namespace Scm.Api.Endpoints;

public sealed record HealthResponse(bool Ok, string Version);

public static class HealthEndpoints
{
    public static IEndpointRouteBuilder MapHealth(this IEndpointRouteBuilder app)
    {
        // M4 додасть перевірки Samba, LDAP і диска.
        app.MapGet("/healthz", () => TypedResults.Ok(new HealthResponse(true, AppVersion.Current)))
            .WithName("GetHealth")
            .WithTags("Health");

        return app;
    }
}
