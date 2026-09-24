using System.Globalization;
using Scm.Api;
using Scm.Api.Endpoints;
using Serilog;

Log.Logger = new LoggerConfiguration()
    .WriteTo.Console(formatProvider: CultureInfo.InvariantCulture)
    .CreateBootstrapLogger();

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
        options.SwaggerDoc("v1", new() { Title = "School Class Manager API", Version = AppVersion.Current }));

    var app = builder.Build();

    app.UseSerilogRequestLogging();
    app.UseSwagger();
    app.UseDefaultFiles();
    app.UseStaticFiles();

    app.MapHealth();
    app.MapFallbackToFile("index.html");

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
