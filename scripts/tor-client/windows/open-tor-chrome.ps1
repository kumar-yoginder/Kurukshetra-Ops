# Launch a separate Chrome profile with proxy-side DNS over the active tunnel.
[CmdletBinding()]
param([uri]$Url = 'http://pzhdfe7jraknpj2qgu5cz2u3i4deuyfwmonvzu5i3nyw4t4bmg7o5pad.onion/')
$ErrorActionPreference = 'Stop'
if ($Url.Scheme -notin @('http','https')) { throw 'Only HTTP and HTTPS URLs are supported.' }
$service = Get-Service -Name 'WireGuardTunnel$kurukshetra-tor' -ErrorAction SilentlyContinue
if (-not $service -or $service.Status -ne 'Running') { throw 'Connect the managed Tor tunnel first.' }
$paths = @(
    (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe'),
    (Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe')
)
$chrome = $paths | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $chrome) { throw 'Chrome was not found in its usual installation paths.' }
$profileDirectory = Join-Path $env:LOCALAPPDATA 'Kurukshetra-Tor-Chrome'
$arguments = @(
    ('--user-data-dir="' + $profileDirectory + '"'),
    '--proxy-server=socks5://10.77.0.1:9050',
    '--host-resolver-rules="MAP * ~NOTFOUND, EXCLUDE 10.77.0.1"',
    '--disable-quic',
    $Url.AbsoluteUri
)
Start-Process -FilePath $chrome -ArgumentList $arguments
Write-Output 'Opened a separate Chrome profile through the tunnel SOCKS endpoint. This does not add Tor Browser fingerprint protections.'
