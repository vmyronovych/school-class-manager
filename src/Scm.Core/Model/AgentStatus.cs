namespace Scm.Core.Model;

public sealed record AgentStatus(string ComputerName, string? Domain, string WindowsEdition, string WindowsBuild,
    decimal? SystemDriveFreeGiB, int? NonSystemProfileCount, bool? SharedPcEnabled, string? AgentVersion = null);
