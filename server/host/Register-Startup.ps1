[CmdletBinding(SupportsShouldProcess)]
param([string]$Project = "$PSScriptRoot/..", [string]$Vagrant = 'C:/Program Files/Vagrant/bin/vagrant.exe')
$ErrorActionPreference = 'Stop'
$Project = [IO.Path]::GetFullPath($Project)
if (-not (Test-Path -LiteralPath $Vagrant)) { throw 'Pass the actual Vagrant executable path' }
if ($PSCmdlet.ShouldProcess('ClassroomServer', 'Register logon task for current teacher user')) {
  $action = New-ScheduledTaskAction -Execute $Vagrant -Argument 'up server --no-provision' -WorkingDirectory $Project
  $trigger = New-ScheduledTaskTrigger -AtLogOn -User ([Security.Principal.WindowsIdentity]::GetCurrent().Name)
  $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
  Register-ScheduledTask -TaskName 'ClassroomServer' -Action $action -Trigger $trigger -Settings $settings -Description 'Start existing classroom DC; never reprovision at logon' -Force | Out-Null
}
