using System.Net;
using System.Net.Http.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using NSubstitute;
using Scm.Api.Endpoints;
using Scm.Core.Ports;

namespace Scm.Api.Tests;

public sealed class PupilApiTests
{
    [Theory]
    [InlineData("/api/students/student1/files")]
    [InlineData("/api/students/student1/download?path=lesson.txt")]
    public async Task AnonymousCannotAccessPupilFiles(string path)
    {
        await using var factory = new PanelFactory();
        using var client = factory.Client();
        using var response = await client.GetAsync(new Uri(path, UriKind.Relative));
        response.StatusCode.Should().Be(HttpStatusCode.Unauthorized);
        await factory.Files.DidNotReceiveWithAnyArgs().ListFilesAsync(default!, default!, default!, default);
        await factory.Files.DidNotReceiveWithAnyArgs().DownloadAsync(default!, default!, default!, default);
    }

    [Fact]
    public async Task TeacherDownloadsAttachmentWithoutCachingAndWithAuthenticatedActor()
    {
        await using var factory = new PanelFactory();
        using var client = factory.Client();
        await SignIn(client);
        using var list = await client.GetAsync(new Uri("/api/students/student1/files?path=lesson", UriKind.Relative));
        list.StatusCode.Should().Be(HttpStatusCode.OK);
        await factory.Files.Received(1).ListFilesAsync(Arg.Is<TeacherSession>(a => a.Login == "teacher1" && a.Sid == "S-1-5-21-1-2-3-1234"), "student1", "lesson", Arg.Any<CancellationToken>());
        using var response = await client.GetAsync(new Uri("/api/students/student1/download?path=lesson%2Fwork.html", UriKind.Relative));
        response.StatusCode.Should().Be(HttpStatusCode.OK);
        response.Content.Headers.ContentType!.MediaType.Should().Be("application/octet-stream");
        response.Content.Headers.ContentDisposition!.DispositionType.Should().Be("attachment");
        response.Content.Headers.ContentDisposition.FileNameStar.Should().Be("Робота.html");
        response.Headers.CacheControl!.NoStore.Should().BeTrue();
        (await response.Content.ReadAsByteArrayAsync()).Should().Equal(new byte[] { 0, 1, 255 });
        await factory.Files.Received(1).DownloadAsync(Arg.Is<TeacherSession>(a => a.Login == "teacher1"), "student1", "lesson/work.html", Arg.Any<CancellationToken>());
        factory.Files.DownloadAsync(Arg.Any<TeacherSession>(), Arg.Any<string>(), Arg.Any<string>(), Arg.Any<CancellationToken>())
            .Returns<Task<PupilDownload>>(_ => throw new DirectoryOperationException("forbidden"));
        using var revoked = await client.GetAsync(new Uri("/api/students/student1/download?path=lesson.txt", UriKind.Relative));
        revoked.StatusCode.Should().Be(HttpStatusCode.Forbidden);
    }

    [Fact]
    public async Task ReportsAreBoundToRegisteredDeviceAndCanOnlyBeReadByStaff()
    {
        var state = System.IO.Directory.CreateTempSubdirectory();
        try
        {
            await using var factory = new PanelFactory();
            await using var scoped = factory.WithWebHostBuilder(b => b.ConfigureServices(services =>
                services.AddSingleton(new Scm.Infrastructure.DeviceReports(state.FullName))));
            using var client = scoped.CreateClient(new WebApplicationFactoryClientOptions { BaseAddress = new Uri("https://localhost") });
            (await client.GetAsync(new Uri("/api/devices", UriKind.Relative))).StatusCode.Should().Be(HttpStatusCode.Unauthorized);
            await SignIn(client);
            await Csrf(client);
            var actor = new TeacherSession("teacher1", "Teacher", "Teacher", "sid");
            factory.Directory.SessionAsync(Arg.Any<TeacherSession>(), Arg.Any<CancellationToken>()).Returns(actor);
            var registration = new RegisterDevice("PC-A", false);
            (await client.PostAsJsonAsync("/api/devices", registration)).StatusCode.Should().Be(HttpStatusCode.Forbidden);
            factory.Directory.SessionAsync(Arg.Any<TeacherSession>(), Arg.Any<CancellationToken>()).Returns(actor with { Role = "Admin" });
            using var created = await client.PostAsJsonAsync("/api/devices", registration);
            created.EnsureSuccessStatusCode();
            var key = (await created.Content.ReadFromJsonAsync<ReportKey>())!.Key;
            var status = new Scm.Core.Model.AgentStatus("PC-A", "school.test", "Windows", "19043", 77, 4, false);
            (await client.PostAsJsonAsync("/agent/status", status)).StatusCode.Should().Be(HttpStatusCode.Unauthorized);
            using var device = scoped.CreateClient(new WebApplicationFactoryClientOptions { BaseAddress = new Uri("https://localhost") });
            device.DefaultRequestHeaders.Authorization = new("Bearer", key);
            (await client.PostAsJsonAsync("/api/devices", registration with { ComputerName = "PC-B" })).EnsureSuccessStatusCode();
            (await device.PostAsJsonAsync("/agent/status", status with { ComputerName = "PC-B" })).StatusCode.Should().Be(HttpStatusCode.Unauthorized);
            (await device.PostAsJsonAsync("/agent/status", status)).StatusCode.Should().Be(HttpStatusCode.NoContent);
            var devices = await client.GetFromJsonAsync<Scm.Infrastructure.DeviceView[]>("/api/devices");
            var pc = devices!.Single(d => d.ComputerName == "PC-A");
            pc.ReceivedAt.Should().NotBeNull();
            pc.Status.Should().Be(status);
            (await client.PostAsJsonAsync("/api/devices", registration with { Replace = true })).EnsureSuccessStatusCode();
            (await device.PostAsJsonAsync("/agent/status", status)).StatusCode.Should().Be(HttpStatusCode.Unauthorized);
        }
        finally { state.Delete(true); }
    }

    [Fact]
    public async Task AnonymousCannotReadStudents()
    {
        await using var factory = new PanelFactory();
        using var client = factory.Client();
        using var response = await client.GetAsync(new Uri("/api/students", UriKind.Relative));
        response.StatusCode.Should().Be(HttpStatusCode.Unauthorized);
    }

    [Fact]
    public async Task LoginRequiresCsrfAndDoesNotCallDirectoryWithoutIt()
    {
        await using var factory = new PanelFactory();
        using var client = factory.Client();
        using var response = await client.PostAsJsonAsync("/api/auth/login", new LoginRequest("teacher1", "example-only"));
        response.StatusCode.Should().Be(HttpStatusCode.BadRequest);
        await factory.Directory.DidNotReceiveWithAnyArgs().AuthenticateAsync(default!, default!, default);
    }

    [Fact]
    public async Task TeacherCanListCreateAndResetWithFreshCsrf()
    {
        await using var factory = new PanelFactory();
        using var client = factory.Client();
        await SignIn(client);
        using var list = await client.GetAsync(new Uri("/api/students", UriKind.Relative));
        list.StatusCode.Should().Be(HttpStatusCode.OK);
        list.Headers.CacheControl!.NoStore.Should().BeTrue();
        var pupils = await list.Content.ReadFromJsonAsync<PupilAccount[]>();
        pupils!.Single().Login.Should().Be("student1");
        await Csrf(client);
        using var created = await client.PostAsJsonAsync("/api/students", new CreatePupil("student3", "Іван", "Петренко"));
        created.StatusCode.Should().Be(HttpStatusCode.OK);
        using var reset = await client.PostAsJsonAsync("/api/students/student1/reset-password", new { });
        reset.StatusCode.Should().Be(HttpStatusCode.OK);
        await factory.Directory.Received(1).CreateAsync(Arg.Is<TeacherSession>(a => a.Login == "teacher1"), Arg.Any<CreatePupil>(), Arg.Any<CancellationToken>());
        using var logout = await client.PostAsJsonAsync("/api/auth/logout", new { });
        logout.StatusCode.Should().Be(HttpStatusCode.NoContent);
        using var after = await client.GetAsync(new Uri("/api/students", UriKind.Relative));
        after.StatusCode.Should().Be(HttpStatusCode.Unauthorized);
    }

    [Fact]
    public async Task MutationWithoutCsrfDoesNotReachDirectory()
    {
        await using var factory = new PanelFactory();
        using var client = factory.Client();
        await SignIn(client);
        client.DefaultRequestHeaders.Remove("X-CSRF-TOKEN");
        using var response = await client.PostAsJsonAsync("/api/students/student1/reset-password", new { });
        response.StatusCode.Should().Be(HttpStatusCode.BadRequest);
        await factory.Directory.DidNotReceiveWithAnyArgs().ResetAsync(default!, default!, default);
    }

    [Fact]
    public async Task RevokedRoleIsRejectedByDirectoryAndErrorDoesNotLeakDetails()
    {
        await using var factory = new PanelFactory();
        using var client = factory.Client();
        await SignIn(client);
        factory.Directory.ListAsync(Arg.Any<TeacherSession>(), Arg.Any<CancellationToken>())
            .Returns<Task<IReadOnlyList<PupilAccount>>>(_ => throw new DirectoryOperationException("forbidden"));
        using var response = await client.GetAsync(new Uri("/api/students", UriKind.Relative));
        response.StatusCode.Should().Be(HttpStatusCode.Forbidden);
        (await response.Content.ReadAsStringAsync()).Should().Be("{\"code\":\"forbidden\"}");
    }

    private static async Task Csrf(HttpClient client)
    {
        var token = await client.GetFromJsonAsync<CsrfResponse>("/api/auth/csrf");
        client.DefaultRequestHeaders.Remove("X-CSRF-TOKEN");
        client.DefaultRequestHeaders.Add("X-CSRF-TOKEN", token!.Token);
    }

    private static async Task SignIn(HttpClient client)
    {
        await Csrf(client);
        using var response = await client.PostAsJsonAsync("/api/auth/login", new LoginRequest("teacher1", "example-only"));
        response.StatusCode.Should().Be(HttpStatusCode.OK);
        response.Headers.GetValues("Set-Cookie").Single().Should().Contain("secure").And.Contain("httponly");
    }

    private sealed class PanelFactory : WebApplicationFactory<Program>
    {
        public IStudentAdministration Directory { get; } = Substitute.For<IStudentAdministration>();
        public IStudentFiles Files { get; } = Substitute.For<IStudentFiles>();

        public PanelFactory()
        {
            Files.ListFilesAsync(Arg.Any<TeacherSession>(), Arg.Any<string>(), Arg.Any<string>(), Arg.Any<CancellationToken>())
                .Returns(Array.Empty<PupilFileEntry>());
            Files.DownloadAsync(Arg.Any<TeacherSession>(), Arg.Any<string>(), Arg.Any<string>(), Arg.Any<CancellationToken>())
                .Returns(new PupilDownload("Робота.html", new byte[] { 0, 1, 255 }));
            var teacher = new TeacherSession("teacher1", "Учитель", "Teacher", "S-1-5-21-1-2-3-1234");
            Directory.AuthenticateAsync(Arg.Any<string>(), Arg.Any<string>(), Arg.Any<CancellationToken>()).Returns(teacher);
            Directory.ListAsync(Arg.Any<TeacherSession>(), Arg.Any<CancellationToken>())
                .Returns(new[] { new PupilAccount("student1", "Учень", true, null) });
            Directory.CreateAsync(Arg.Any<TeacherSession>(), Arg.Any<CreatePupil>(), Arg.Any<CancellationToken>())
                .Returns(new PupilCredentials("student3", "example-created-secret"));
            Directory.ResetAsync(Arg.Any<TeacherSession>(), Arg.Any<string>(), Arg.Any<CancellationToken>())
                .Returns(new PupilCredentials("student1", "example-reset-secret"));
        }

        public HttpClient Client() => CreateClient(new WebApplicationFactoryClientOptions { BaseAddress = new Uri("https://localhost"), AllowAutoRedirect = false });

        protected override void ConfigureWebHost(IWebHostBuilder builder) => builder.ConfigureServices(services =>
        {
            services.RemoveAll<IStudentAdministration>();
            services.AddSingleton(Directory);
            services.RemoveAll<IStudentFiles>();
            services.AddSingleton(Files);
        });
    }
}
