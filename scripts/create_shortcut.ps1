$root = Split-Path -Parent $PSScriptRoot
$desktop = [Environment]::GetFolderPath("Desktop")
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut((Join-Path $desktop "NOVA AI.lnk"))
$shortcut.TargetPath = Join-Path $root "START_NOVA.bat"
$shortcut.WorkingDirectory = $root
$shortcut.WindowStyle = 7
$shortcut.Description = "NOVA AI"
$shortcut.Save()
Write-Output "NOVA AI kisayolu masaustune yazildi."
