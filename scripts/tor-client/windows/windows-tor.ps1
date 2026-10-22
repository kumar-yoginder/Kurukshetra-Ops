# Windows client prototype. Run from the VM console in Administrator PowerShell.
# Requires official WireGuard for Windows and an individually provisioned profile.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('Install','Connect','Status','Check','Disconnect','Browser','Update')][string]$Action,
    [string]$ConfigPath
)
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Use Administrator PowerShell from the local VM console.'
}
$wireguard = Join-Path $env:ProgramFiles 'WireGuard\wireguard.exe'
$directory = Join-Path $env:ProgramData 'KurukshetraTor'
$peerFile = Join-Path $directory 'kurukshetra-tor.conf'
$serviceName = 'WireGuardTunnel$kurukshetra-tor'
function Copy-ClientTools {
    $helper = Join-Path $PSScriptRoot 'open-tor-browser.ps1'
    if (-not (Test-Path -LiteralPath $helper)) { throw 'Download open-tor-browser.ps1 beside windows-tor.ps1 first.' }
    $target = Join-Path $directory 'windows-tor.ps1'
    if ($PSCommandPath -ine $target) { Copy-Item -LiteralPath $PSCommandPath -Destination $target -Force }
    $target = Join-Path $directory 'open-tor-browser.ps1'
    if ($helper -ine $target) { Copy-Item -LiteralPath $helper -Destination $target -Force }
}
function Open-ManagedBrowser {
    $helper = Join-Path $directory 'open-tor-browser.ps1'
    if ($identity.IsSystem -or $env:SSH_CONNECTION) { Write-Output 'Headless/remote session: run the Browser action locally when ready.'; return }
    if (-not (Test-Path -LiteralPath $helper)) { Write-Warning 'Browser helper missing; run Update with both downloaded scripts.'; return }
    try { & $helper } catch { Write-Warning ('Tunnel remains connected; browser launch failed: ' + $_.Exception.Message) }
}
function Invoke-TunnelCommand([string]$Operation, [string]$Value) {
    # WireGuard is a GUI-subsystem executable; explicitly wait for CLI completion.
    $process = Start-Process -FilePath $wireguard -ArgumentList @('/' + $Operation, ('"' + $Value + '"')) -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw ('WireGuard command failed: ' + $Operation + ' exit ' + $process.ExitCode) }
}
function Validate-Peer([string]$Path) {
    $content = Get-Content -LiteralPath $Path -Raw
    if ([regex]::Matches($content, '(?im)^\s*\[Peer\]\s*$').Count -ne 1 -or
        [regex]::Matches($content, '(?im)^\s*\[Interface\]\s*$').Count -ne 1) {
        throw 'Exactly one Interface and one Peer are required.'
    }
    $values = @{}
    foreach ($line in ($content -split '\r?\n')) {
        if ($line -match '^\s*(?:#.*|\[.*\])?\s*$') { continue }
        if ($line -notmatch '^\s*(\w+)\s*=\s*(.+?)\s*$') { throw 'Invalid profile line.' }
        $key = $Matches[1]; $value = $Matches[2]
        if ($key -notin @('PrivateKey','Address','DNS','PublicKey','PresharedKey','Endpoint','AllowedIPs','PersistentKeepalive','MTU') -or $values.ContainsKey($key)) {
            throw 'Unsupported or duplicate profile setting.'
        }
        $values[$key] = $value
    }
    foreach ($key in @('PrivateKey','PublicKey')) {
        if ($values[$key] -notmatch '^[A-Za-z0-9+/]{43}=$') { throw 'Missing or invalid peer key.' }
    }
    $routes = @($values['AllowedIPs'] -split ',' | ForEach-Object { $_.Trim() } | Sort-Object)
    if ($routes.Count -ne 2 -or $routes -notcontains '0.0.0.0/0' -or $routes -notcontains '::/0') { throw 'Require AllowedIPs = 0.0.0.0/0, ::/0 for the full-tunnel guard.' }
    if ($values['DNS'] -ne '10.77.0.1') { throw 'Require gateway DNS 10.77.0.1.' }
    if ($values['Address'] -notmatch '^10\.77\.0\.(\d{1,3})/32$') { throw 'Require an assigned client /32 address.' }
    $number = [int]$Matches[1]
    if ($number -lt 2 -or $number -gt 254 -or -not $values['Endpoint']) { throw 'Invalid client assignment or missing endpoint.' }
}
switch ($Action) {
    'Install' {
        if (-not (Test-Path -LiteralPath $wireguard)) { throw 'Install official WireGuard for Windows first.' }
        if (-not $ConfigPath -or -not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) { throw 'Supply -ConfigPath to your private peer configuration.' }
        if (Test-Path -LiteralPath $directory) { throw 'Existing private installation: review it instead of overwriting.' }
        if (-not (Test-Path (Join-Path $PSScriptRoot 'open-tor-browser.ps1'))) { throw 'Download the browser helper beside this script first.' }
        Validate-Peer $ConfigPath
        New-Item -ItemType Directory -Path $directory | Out-Null
        $acl = New-Object Security.AccessControl.DirectorySecurity
        $acl.SetAccessRuleProtection($true,$false)
        foreach ($sid in @('S-1-5-18','S-1-5-32-544')) {
            $account = New-Object Security.Principal.SecurityIdentifier($sid)
            $rule = New-Object Security.AccessControl.FileSystemAccessRule($account,'FullControl','ContainerInherit,ObjectInherit','None','Allow')
            $acl.AddAccessRule($rule)
        }
        Set-Acl -LiteralPath $directory -AclObject $acl
        Copy-Item -LiteralPath $ConfigPath -Destination $peerFile
        Copy-ClientTools
        Write-Output 'Private configuration installed. Networking unchanged. Connect separately from the VM console.'
    }
    'Connect' {
        if (-not (Test-Path -LiteralPath $wireguard)) { throw 'Official WireGuard is not installed.' }
        Validate-Peer $peerFile
        if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) { throw 'A managed tunnel already exists; inspect Status first.' }
        Invoke-TunnelCommand 'installtunnelservice' $peerFile
        try {
            Set-Service -Name $serviceName -StartupType Manual
            (Get-Service -Name $serviceName).WaitForStatus('Running',[TimeSpan]::FromSeconds(15))
        } catch {
            $failure = $_
            try { Invoke-TunnelCommand 'uninstalltunnelservice' 'kurukshetra-tor' } catch { Write-Warning 'Automatic cleanup failed; use Disconnect locally.' }
            throw $failure
        }
        Write-Output 'Tunnel running with manual startup. Run Check. Local network access may be blocked; keep the VM console available.'
        Open-ManagedBrowser
    }
    'Update' {
        Validate-Peer $peerFile
        Copy-ClientTools
        Write-Output 'Controller and browser helper updated; private profile and networking unchanged.'
    }
    'Browser' {
        if ((Get-Service -Name $serviceName).Status -ne 'Running') { throw 'Connect the managed tunnel first.' }
        Open-ManagedBrowser
    }
    'Status' {
        $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
        if ($service) { $service | Select-Object Status,StartType,DisplayName }
        else { Write-Output 'No managed tunnel service. Ordinary networking may be active.' }
    }
    'Check' {
        if ((Get-Service -Name $serviceName).Status -ne 'Running') { throw 'Managed tunnel is not running.' }
        $result = Invoke-RestMethod -Uri 'https://check.torproject.org/api/ip' -TimeoutSec 35
        if ($result.IsTor -ne $true) { throw 'Tor egress not verified.' }
        Write-Output ('Tor verified; check-stream exit IP: ' + $result.IP)
    }
    'Disconnect' {
        if (-not (Test-Path -LiteralPath $wireguard)) { throw 'Official WireGuard is not installed.' }
        if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {
            Invoke-TunnelCommand 'uninstalltunnelservice' 'kurukshetra-tor'
        }
        Write-Output 'Managed tunnel removed. Ordinary networking is restored; private profile retained.'
    }
}
