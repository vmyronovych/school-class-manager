# GPO logon-скрипт (User Configuration → Scripts → Logon).
# Поточний клас = група uchni-<рік>-<клас> з найновішим роком. Створює
# \\dc1\class\<рік>-<клас>\submit\<login> і ярлик «Роздатки» на поточний клас.
$login = $env:USERNAME
$cls = [Security.Principal.WindowsIdentity]::GetCurrent().Groups |
  ForEach-Object {
    try { $name = $_.Translate([Security.Principal.NTAccount]).Value } catch { return }
    if ($name -match '\\uchni-(\d{4}-\d{1,2}[a-z])$') { $Matches[1] }
  } | Sort-Object -Descending | Select-Object -First 1
if (-not $cls) { exit }
$dir = "\\dc1\class\$cls\submit\$login"
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
$lnk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Роздатки.lnk'
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
if ($s.TargetPath -ne "\\dc1\class\$cls\handouts") {
  $s.TargetPath = "\\dc1\class\$cls\handouts"
  $s.Save()
}
