# Windows Tor client prototype

The PowerShell parser and profile-validator logic were exercised on the restored Windows 11 ARM64 VM. Full tunnel installation and egress/leak tests remain pending. Ubuntu trial results do not establish Windows leak protection. Keep the Fusion console available before testing; full-tunnel firewall rules can block remote administration.

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
