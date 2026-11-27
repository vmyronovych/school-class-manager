using System.Net;
using System.Net.Http.Json;
using Microsoft.AspNetCore.Mvc.Testing;
using Scm.Api;
using Scm.Api.Endpoints;

namespace Scm.Api.Tests;

public class HealthzTests(WebApplicationFactory<Program> factory) : IClassFixture<WebApplicationFactory<Program>>
{
    [Fact]
    public async Task ReturnsOkWithVersionFromBuildProps()
    {
        using var client = factory.CreateClient();
        using var response = await client.GetAsync(new Uri("/healthz", UriKind.Relative));

        response.StatusCode.Should().Be(HttpStatusCode.OK);
        var health = await response.Content.ReadFromJsonAsync<HealthResponse>();
        health.Should().Be(new HealthResponse(true, AppVersion.Current));
    }
}
