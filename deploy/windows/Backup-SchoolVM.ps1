#requires -RunAsAdministrator
#requires -Modules Hyper-V
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Destination,
    [string]$VMName = 'school-server'
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $Destination).ProviderPath
$vm = Get-VM -Name $VMName -ErrorAction Stop
if ($vm.State -notin 'Running', 'Off') { throw "Unexpected VM state: $($vm.State)" }
$started = $vm.State -eq 'Running'
$stamp = [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')
$stage = Join-Path $root "$VMName-$stamp.partial"
$lock = [IO.File]::Open((Join-Path $root "$VMName.lock"), 'OpenOrCreate', 'Write', 'None')
try {
    New-Item -ItemType Directory -Path $stage -ErrorAction Stop | Out-Null
    try {
        if ($started) { Stop-VM -VM $vm -ErrorAction Stop }
        if ((Get-VM -Id $vm.Id).State -ne 'Off') { throw 'The guest has not shut down.' }
        Export-VM -VM $vm -Path $stage
    } finally {
        if ($started -and (Get-VM -Id $vm.Id).State -eq 'Off') { Start-VM -VM $vm }
    }
    if (-not (Get-ChildItem $stage -Recurse -Filter '*.vmcx') -or
        -not (Get-ChildItem $stage -Recurse -Filter '*.vhdx')) { throw 'Incomplete VM export.' }
    Move-Item -LiteralPath $stage -Destination (Join-Path $root "$VMName-$stamp")
} finally {
    $lock.Dispose()
}
