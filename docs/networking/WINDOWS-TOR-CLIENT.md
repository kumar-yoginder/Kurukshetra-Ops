# Windows Tor client prototype

The PowerShell parser and profile-validator logic were exercised on the restored Windows 11 ARM64 VM. A bounded manual-session trial subsequently passed Tor HTTPS verification, tunnel DNS, routing, an IPv6 connection block, and automatic disconnect. Broader outage/leak/reboot tests remain pending. Ubuntu trial results do not establish Windows leak protection. Keep the Fusion console available before testing; full-tunnel firewall rules can block remote administration.

Install official WireGuard for Windows and trust the local gateway CA. Review `scripts/tor-client/windows/windows-tor.ps1` and respect local PowerShell policy. Provision a unique private Windows profile with Address in the assigned tunnel range as /32, gateway DNS, one peer, and AllowedIPs containing both IPv4 and IPv6 default routes. Server AllowedIPs must match that client /32. Never publish keys or reuse another device private key.

From Administrator PowerShell at the VM console:

```powershell
.\windows-tor.ps1 -Action Install -ConfigPath 'C:\Private\windows-peer.conf'
.\windows-tor.ps1 -Action Connect
.\windows-tor.ps1 -Action Status
.\windows-tor.ps1 -Action Check
.\windows-tor.ps1 -Action Disconnect
```

Install stores the private profile under an Administrators/SYSTEM-only directory in ProgramData without changing networking. Connect uses the official tunnel-service command and sets manual startup. Disconnect removes only that named service and retains private configuration. No timed rollback is implemented. Reboot or disconnect can restore ordinary direct networking. Tor supports application TCP and gateway DNS; generic UDP applications are not supported. The gateway drops client IPv6 rather than providing IPv6 egress.

Before declaring ready, test official client compatibility, DNS and IPv6 leaks, gateway outage with no direct fallback, manual recovery, and reboot behavior on a disposable/snapshotted VM. No such tests have been performed.

References: [official service commands](https://git.zx2c4.com/wireguard-windows/about/docs/enterprise.md), [official full-tunnel firewall behavior](https://github.com/WireGuard/wireguard-windows/blob/master/docs/netquirk.md).

## Windows prerequisite checkpoint

Operator restored the selected existing snapshot and authorized Mac SSH access locally. Administrator SSH works. Official WireGuard ARM64 1.1.1 was installed after Authenticode status and publisher verification. PowerShell parser passed. Runtime validator testing found a culture-dependent route-sort comparison; membership checks now accept the intended full-tunnel profile and reject split routes. No private peer or active tunnel has been installed. Guest main adapter still needed reachability to the Pi at this checkpoint; host-only management remains separate.

## Peer preparation checkpoint

Windows now reaches the Pi after returning to home-LAN DHCP. A new private Windows key and profile were generated inside an Administrators/SYSTEM-only staging directory. Script installation was blocked by the existing PowerShell execution policy; no policy override or tunnel connection was performed. Only the public key was transferred to ignored Pi registration input. Persistent registration requires operator sudo via `sudo python3 scripts/tor-gateway/register-peer.py config/tor-gateway/private/windows-peer.json`. The helper validates unique assignment and updates runtime and root-owned configuration without restarting the gateway. No connection tests are complete yet.

## Corrected live manual-session trial

The first trial exposed a command-completion race: the controller invoked the WireGuard GUI-subsystem executable without explicitly waiting before inspecting exit status. The controller now uses Start-Process with Wait and PassThru for installation/removal. A second local SYSTEM task reported connected=true, tor_verified=true, dns_configured=true, dns_resolved=true, tunnel_route=true, direct_ipv6_connected=false, disconnected=true, and no runtime or cleanup error. SSH returned after disconnect. Temporary test and recovery tasks were removed, the user-facing controller was updated, and saved PowerShell execution-policy scopes remained unchanged.

Current state after testing: disconnected, ordinary networking restored. This does not establish gateway-outage behavior, comprehensive DNS leak resistance, or reboot privacy. A reusable local test body is retained as windows/test-session.ps1; it expects the protected controller under ProgramData and must only be run with independently armed recovery.

[Microsoft process-wait behavior](https://devblogs.microsoft.com/powershell/managing-processes-in-powershell/).

## Onion browsing in Chrome

The gateway itself retrieved the official Tor blog onion with HTTP 200 and resolved its virtual DNS mapping. Stock curl rejected direct onion resolution even with a supplied address; that was an unsuitable client test. Use `curl.exe --socks5-hostname 10.77.0.1:9050` while connected. The Tor SOCKS listener on the tunnel address is accepted only from wg0; Docker still publishes only WireGuard UDP. The local probe SOCKS listener remains loopback-only.

`windows/open-tor-browser.ps1` opens a separate Chrome profile with SOCKS5, proxy-side DNS and QUIC disabled. It does not alter the system proxy or provide Tor Browser fingerprint protections. Download it before connecting because local gateway HTTPS is intentionally unavailable under the full-tunnel policy. End-to-end Windows onion/browser verification is pending. [Chromium proxy documentation](https://chromium.googlesource.com/chromium/src/net/+/show/HEAD/docs/proxy.md).

## Automatic installed-browser integration

Download windows-tor.ps1 and open-tor-browser.ps1 together. Install now saves both under the private ProgramData directory; existing installations use Action Update to refresh only code, preserving peer configuration and network state. Connect from the local desktop attempts an installed Chrome, Edge or Chromium using a separate Tor browser profile; it does not edit the normal profile or Windows global proxy. Browser explicitly opens the same helper. SYSTEM/SSH sessions skip automatic GUI launch. If no supported browser is present, report that condition without installing anything.

The operator confirmed onion access using the SOCKS5 Chrome command. This confirms that path, not Tor Browser fingerprint protections. RemoteSigned was authorized only for temporary processes; saved policy remains unchanged.

## Automatic browser desktop trial

The updated controller and browser helper were installed without changing peer settings. A local interactive-user scheduled trial reported connected=true, browser_started=true, tor_verified=true, disconnected=true, error=null. The VM screen showed the official onion blog loaded in the launched Chrome window. Both temporary trial/recovery tasks were removed; Windows was left disconnected. Chrome displayed its warning about the advanced host-resolver-rules flag; no warning was suppressed. The source and downloads retain that explicit proxy-side DNS configuration.
