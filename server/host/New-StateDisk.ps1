[CmdletBinding(SupportsShouldProcess)]
param([string]$Config = "$PSScriptRoot/../config.local.json", [string]$VBoxManage = 'C:/Program Files/Oracle/VirtualBox/VBoxManage.exe')
$ErrorActionPreference = 'Stop'
$c = Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
if (-not [IO.Path]::IsPathRooted($c.state_disk)) { throw 'state_disk must be absolute' }
$target = [IO.Path]::GetFullPath($c.state_disk)
$checkout = [IO.Path]::GetFullPath("$PSScriptRoot/../..").TrimEnd('\') + '\'
if ($target.StartsWith($checkout, [StringComparison]::OrdinalIgnoreCase)) { throw 'Store state outside checkout' }
if (Test-Path -LiteralPath $target) { Write-Output 'Existing disk retained; no resize/format performed.'; return }
if ($c.state_disk_mb -lt 8192) { throw 'State disk must be at least 8192 MB' }
if ($PSCmdlet.ShouldProcess($target, 'Create new empty persistent VDI')) {
  New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
  & $VBoxManage createmedium disk --filename $target --size $c.state_disk_mb --format VDI --variant Standard
  if ($LASTEXITCODE -ne 0) { throw 'VDI creation failed' }
  Write-Output 'Disk created. Explicitly set initialize_storage=true for first guest format, then false.'
}
