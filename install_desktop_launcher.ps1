$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcherPath = Join-Path $projectRoot 'Launch_SOC_Copilot.vbs'
$iconPath = Join-Path $projectRoot 'assets\icon.ico'
$desktopPath = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktopPath 'SOC Copilot.lnk'

if (-not (Test-Path $launcherPath)) {
    throw "Launcher not found: $launcherPath"
}

$wshShell = New-Object -ComObject WScript.Shell
$shortcut = $wshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $launcherPath
$shortcut.WorkingDirectory = $projectRoot
$shortcut.IconLocation = if (Test-Path $iconPath) { $iconPath } else { "$env:SystemRoot\System32\shell32.dll,220" }
$shortcut.Description = 'Launch SOC Copilot'
$shortcut.Save()

Write-Host "Desktop launcher created: $shortcutPath"
