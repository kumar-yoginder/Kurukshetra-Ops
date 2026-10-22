# Install per-user GUI entry points; no system-wide proxy or saved-policy changes.
$ErrorActionPreference = 'Stop'
$paths = @(
    (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe'),
    (Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe'),
    (Join-Path $env:ProgramFiles 'Microsoft\Edge\Application\msedge.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe'),
    (Join-Path $env:LOCALAPPDATA 'Chromium\Application\chrome.exe')
)
$browser = $paths | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $browser) { throw 'No supported installed browser found.' }
$controller = Join-Path $env:ProgramData 'KurukshetraTor\windows-tor.ps1'
if (-not (Test-Path -LiteralPath $controller)) { throw 'Install the private client first.' }
$powershell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$profileDirectory = Join-Path $env:LOCALAPPDATA 'Kurukshetra-Tor-Browser'
$desktop = [Environment]::GetFolderPath('DesktopDirectory')
$startMenu = Join-Path ([Environment]::GetFolderPath('Programs')) 'Kurukshetra Tor'
$shell = New-Object -ComObject WScript.Shell
foreach ($folder in @($desktop,$startMenu)) {
    New-Item -ItemType Directory -Force -Path $folder | Out-Null
    foreach ($action in @('Connect','Stop','Uninstall')) {
        # Encoding only avoids nested shortcut/PowerShell quoting. UAC is retained.
        $elevation = "Start-Process -FilePath '$powershell' -Verb RunAs -ArgumentList @('-NoProfile','-ExecutionPolicy','RemoteSigned','-File','`"$controller`"','-Action','$action')"
        $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($elevation))
        $shortcut = $shell.CreateShortcut((Join-Path $folder ($action + ' Tor.lnk')))
        $shortcut.TargetPath = $powershell
        $shortcut.Arguments = '-NoProfile -EncodedCommand ' + $encoded
        $shortcut.WorkingDirectory = $env:USERPROFILE
        $shortcut.Description = $action + ' the managed Tor tunnel (administrator confirmation required).'
        $shortcut.IconLocation = $browser + ',0'
        $shortcut.Save()
    }
    Remove-Item -LiteralPath (Join-Path $folder 'Disconnect Tor.lnk') -ErrorAction SilentlyContinue
    $shortcut = $shell.CreateShortcut((Join-Path $folder 'Open Tor Browser.lnk'))
    $shortcut.TargetPath = $browser
    $shortcut.Arguments = '--user-data-dir="' + $profileDirectory + '" --proxy-server=socks5://10.77.0.1:9050 --host-resolver-rules="MAP * ~NOTFOUND, EXCLUDE 10.77.0.1" --disable-quic http://pzhdfe7jraknpj2qgu5cz2u3i4deuyfwmonvzu5i3nyw4t4bmg7o5pad.onion/'
    $shortcut.WorkingDirectory = $env:USERPROFILE
    $shortcut.Description = 'Existing browser, separate Tor profile. Connect Tor first. This is not the Tor Browser application.'
    $shortcut.IconLocation = $browser + ',0'
    $shortcut.Save()
}
Write-Output 'Installed Connect Tor, Open Tor Browser, Stop Tor, and Uninstall Tor shortcuts on Desktop and in Start menu.'
