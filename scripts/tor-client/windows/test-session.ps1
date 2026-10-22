$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$directory = Join-Path $env:ProgramData 'KurukshetraTor'
$clientScript = Join-Path $directory 'windows-tor.ps1'
$result = [ordered]@{ connected=$false; tor_verified=$false; dns_configured=$false; dns_resolved=$false; tunnel_route=$false; direct_ipv6_connected=$null; disconnected=$false; error=$null; cleanup_error=$null }
try {
    & $clientScript -Action Connect | Out-Null
    $result.connected = $true
    Start-Sleep -Seconds 4
    $dns = Get-DnsClientServerAddress -InterfaceAlias 'kurukshetra-tor' -AddressFamily IPv4
    $result.dns_configured = $dns.ServerAddresses -contains '10.77.0.1'
    $answer = Resolve-DnsName 'check.torproject.org' -Type A -DnsOnly -ErrorAction Stop
    $result.dns_resolved = @($answer | Where-Object {$_.Type -eq 'A'}).Count -gt 0
    $route = Find-NetRoute -RemoteIPAddress '1.1.1.1'
    $result.tunnel_route = @($route | Where-Object {$_.InterfaceAlias -eq 'kurukshetra-tor'}).Count -gt 0
    $check = Invoke-RestMethod 'https://check.torproject.org/api/ip' -TimeoutSec 35
    $result.tor_verified = $check.IsTor -eq $true
    $ipv6 = New-Object Net.Sockets.TcpClient([Net.Sockets.AddressFamily]::InterNetworkV6)
    try {
        $connection = $ipv6.ConnectAsync([Net.IPAddress]::Parse('2606:4700:4700::1111'),443)
        $result.direct_ipv6_connected = $connection.Wait(8000) -and $ipv6.Connected
    } catch { $result.direct_ipv6_connected = $false }
    finally { $ipv6.Dispose() }
} catch {
    $result.error = $_.Exception.Message
} finally {
    try {
        & $clientScript -Action Disconnect | Out-Null
        $result.disconnected = -not [bool](Get-Service -Name 'WireGuardTunnel$kurukshetra-tor' -ErrorAction SilentlyContinue)
    } catch { $result.cleanup_error = $_.Exception.Message }
    $result | ConvertTo-Json | Set-Content (Join-Path $directory 'trial-result.json') -Encoding UTF8
}
