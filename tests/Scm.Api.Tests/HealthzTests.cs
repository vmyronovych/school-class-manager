using System.Net;
using Microsoft.AspNetCore.Mvc.Testing;

namespace Scm.Api.Tests;

public class HealthzTests(WebApplicationFactory<Program> factory) : IClassFixture<WebApplicationFactory<Program>>
{
    [Fact]
    public async Task ReturnsOkWithVersionFromBuildProps()
    {
        using var client = factory.CreateClient();

        using var response = await client.GetAsync(new Uri("/healthz", UriKind.Relative));

        response.StatusCode.Should().Be(HttpStatusCode.OK);
        var body = await response.Content.ReadAsStringAsync();
        body.Should().Be("""{"ok":true,"version":"0.1.0"}""");
    }
}
