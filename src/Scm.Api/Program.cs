using System.Globalization;
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.DataProtection;
using Scm.Core.Ports;
using Scm.Infrastructure.Process;
using Scm.Api;
using Scm.Api.Endpoints;
using Serilog;

Log.Logger = new LoggerConfiguration()
    .WriteTo.Console(formatProvider: CultureInfo.InvariantCulture)
    .CreateLogger();

try
{
    var builder = WebApplication.CreateBuilder(args);

    // stdout сервісу забирає journald (journalctl -u scm).
    builder.Host.UseSerilog((context, services, configuration) => configuration
        .ReadFrom.Configuration(context.Configuration)
        .ReadFrom.Services(services)
        .Enrich.FromLogContext()
        .WriteTo.Console(formatProvider: CultureInfo.InvariantCulture));

    builder.Services.AddEndpointsApiExplorer();
    builder.Services.AddSwaggerGen(options =>
    {
        options.SupportNonNullableReferenceTypes();
        options.SwaggerDoc("v1", new() { Title = "School Class Manager API", Version = AppVersion.Current });
    });

    builder.Services.AddSingleton<IProcessRunner, ProcessRunner>();
    builder.Services.AddSingleton<SudoRunner>();
    builder.Services.AddSingleton<IStudentAdministration, SambaStudentAdministration>();
    builder.Services.AddSingleton<IStudentFiles, SambaStudentAdministration>();
    builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme).AddCookie(options =>
    {
        options.Cookie.Name = "__Host-scm";
        options.Cookie.HttpOnly = true;
        options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
        options.Cookie.SameSite = SameSiteMode.Strict;
        options.ExpireTimeSpan = TimeSpan.FromMinutes(20);
        options.SlidingExpiration = false;
        options.Events.OnRedirectToLogin = context => { context.Response.StatusCode = 401; return Task.CompletedTask; };
        options.Events.OnRedirectToAccessDenied = context => { context.Response.StatusCode = 403; return Task.CompletedTask; };
    });
    builder.Services.AddAuthorization(options =>
    {
        options.AddPolicy("Teacher", policy => policy.RequireRole("Teacher", "Admin"));
        options.FallbackPolicy = new AuthorizationPolicyBuilder().RequireAuthenticatedUser().Build();
    });
    builder.Services.AddAntiforgery(options =>
    {
        options.HeaderName = "X-CSRF-TOKEN";
        options.Cookie.Name = "__Host-scm-csrf";
        options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
        options.Cookie.SameSite = SameSiteMode.Strict;
    });
    builder.Services.AddRateLimiter(options =>
    {
        options.RejectionStatusCode = 429;
        options.AddPolicy("login", context => RateLimitPartition.GetFixedWindowLimiter(
            context.Connection.RemoteIpAddress?.ToString() ?? "local",
            _ => new FixedWindowRateLimiterOptions { PermitLimit = 5, Window = TimeSpan.FromMinutes(1) }));
    });
    if (builder.Configuration["DataProtectionPath"] is { Length: > 0 } keys)
    {
        builder.Services.AddDataProtection().PersistKeysToFileSystem(new DirectoryInfo(keys));
    }
    builder.WebHost.ConfigureKestrel(options => options.Limits.MaxRequestBodySize = 16 * 1024);

    var app = builder.Build();
    app.UseSerilogRequestLogging();

    app.Use(async (context, next) =>
    {
        context.Response.Headers["X-Content-Type-Options"] = "nosniff";
        context.Response.Headers["Referrer-Policy"] = "no-referrer";
        context.Response.Headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'";
        if (context.Request.Path.StartsWithSegments("/api"))
        {
            context.Response.Headers.CacheControl = "no-store";
        }
        try { await next(context); }
        catch (DirectoryOperationException error)
        {
            context.Response.StatusCode = error.Code switch {
                "credentials" => 401, "forbidden" => 403, "not_found" => 404,
                "exists" => 409, "validation" or "invalid_path" => 400,
                "file_not_found" => 404, "file_too_large" or "too_many_files" => 413, _ => 503,
            };
            await context.Response.WriteAsJsonAsync(new ApiError(error.Code));
        }
        catch (ArgumentException)
        {
            context.Response.StatusCode = 400;
            await context.Response.WriteAsJsonAsync(new ApiError("validation"));
        }
    });
    app.UseSwagger();
    app.UseDefaultFiles();
    app.UseStaticFiles();

    app.UseAuthentication();
    app.UseAuthorization();
    app.UseRateLimiter();
    app.Use(async (context, next) =>
    {
        if (context.Request.Path.StartsWithSegments("/api") && HttpMethods.IsPost(context.Request.Method))
        {
            var csrf = context.RequestServices.GetRequiredService<IAntiforgery>();
            if (!await csrf.IsRequestValidAsync(context))
            {
                context.Response.StatusCode = 400;
                await context.Response.WriteAsJsonAsync(new ApiError("csrf"));
                return;
            }
        }
        await next(context);
    });
    app.MapPupils();
    app.MapPupilFiles();
    app.MapHealth();
    app.MapFallbackToFile("index.html").AllowAnonymous();

    await app.RunAsync();
}
catch (Exception ex) when (ex is not HostAbortedException)
{
    Log.Fatal(ex, "Scm.Api не запустився");
    throw;
}
finally
{
    await Log.CloseAndFlushAsync();
}

public partial class Program;
