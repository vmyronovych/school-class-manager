param([string]$Bash = 'C:/Program Files/Git/bin/bash.exe', [string]$Python = 'python', [string]$Ruby = 'ruby')
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath("$PSScriptRoot/..")
$c = Get-Content -LiteralPath "$root/config.example.json" -Raw | ConvertFrom-Json
if ($c.confirmed -ne $false -or $c.initialize_storage -ne $false -or $c.mode -ne 'lab') { throw 'Unsafe example defaults' }
if ($c.realm -notlike '*.TEST') { throw 'Lab realm must be .TEST' }
$errorsFound = @()
Get-ChildItem -LiteralPath "$root/host" -Filter '*.ps1' | ForEach-Object {
  $tokens = $null; $parseErrors = $null
  [Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$parseErrors) | Out-Null
  $errorsFound += $parseErrors
}
if ($errorsFound.Count) { throw ($errorsFound | Out-String) }
foreach ($file in Get-ChildItem -LiteralPath "$root/scripts" -Filter '*.sh') {
  & $Bash -n $file.FullName
  if ($LASTEXITCODE -ne 0) { throw "Bash parse failed: $file" }
}
foreach ($file in Get-ChildItem -LiteralPath "$root/scripts" -Filter '*.py') {
  & $Python -m py_compile $file.FullName
  if ($LASTEXITCODE -ne 0) { throw "Python parse failed: $file" }
}
& $Ruby -c "$root/Vagrantfile"
if ($LASTEXITCODE -ne 0) { throw 'Ruby parse failed' }
Write-Output 'PASS: safe example defaults and PowerShell/Bash/Python/Ruby syntax. No runtime AD/restore claim.'
