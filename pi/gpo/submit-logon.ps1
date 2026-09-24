# GPO logon-скрипт (User Configuration → Scripts → Logon).
# Створює \\dc1\class\<клас>\submit\<login> при першому вході й ярлик «Роздатки» на Робочому столі.
$login = $env:USERNAME
if ($login -notmatch '^(\d{1,2}[a-z])\.') { exit }
$cls = $Matches[1]
$dir = "\\dc1\class\$cls\submit\$login"
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
$lnk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Роздатки.lnk'
if (-not (Test-Path $lnk)) {
  $s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
  $s.TargetPath = "\\dc1\class\$cls\handouts"
  $s.Save()
}
