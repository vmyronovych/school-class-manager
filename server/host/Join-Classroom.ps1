[CmdletBinding(SupportsShouldProcess, ConfirmImpact='High')]
param([Parameter(Mandatory)][string]$Domain, [Parameter(Mandatory)][ipaddress]$ServerIP,
      [Parameter(Mandatory)][string]$InterfaceAlias, [string]$ComputerName = $env:COMPUTERNAME)
$ErrorActionPreference = 'Stop'
# Run on ONE pupil PC/VM as local admin, never on teacher host automatically.
$saved = Join-Path $env:ProgramData 'Classroom-dns-before.json'
if ($PSCmdlet.ShouldProcess($ComputerName, "Set client DNS to $ServerIP and join $Domain; no automatic restart")) {
  if (Test-Path -LiteralPath $saved) { throw "Existing DNS snapshot at $saved; review it first" }
  Get-DnsClientServerAddress -InterfaceAlias $InterfaceAlias | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $saved
  Set-DnsClientServerAddress -InterfaceAlias $InterfaceAlias -ServerAddresses $ServerIP.IPAddressToString
  try {
    Clear-DnsClientCache
    Resolve-DnsName "_ldap._tcp.dc._msdcs.$Domain" -Type SRV -Server $ServerIP.IPAddressToString | Out-Null
    $credential = Get-Credential -Message 'Domain join admin credential; password stays in memory'
    Add-Computer -DomainName $Domain -NewName $ComputerName -Credential $credential -PassThru -ErrorAction Stop
    Write-Output 'Joined. Save work and explicitly approve a restart before Restart-Computer.'
  } catch {
    Write-Warning "Join failed. Previous DNS settings are in $saved; restore them before retrying."
    throw
  }
}
