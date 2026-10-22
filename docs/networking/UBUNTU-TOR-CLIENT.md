# Ubuntu Tor client: manual sessions

Validated on Ubuntu Server 24.04 ARM64. These scripts are not a Windows or universal Linux installer. They do not provide Tor Browser's protections.

## First setup on a new target

1. Provision an individual WireGuard peer on the Pi, with a unique tunnel address. Set `CLIENT_TUNNEL_IP` in the private `local.env` to a unique address in `10.77.0.2` through `10.77.0.254`. Configure the corresponding server peer with exactly that address as `/32` AllowedIPs. The script validates the range but cannot verify remote peer assignments or detect duplicate allocations. Never reuse the tested guest's private key on another VM.
2. Install prerequisites: `wireguard-tools`, `nftables`, `iproute2`; systemd-resolved and systemd must already be present.
3. Copy `scripts/tor-client/ubuntu/trial.sh` and `tor-client.sh` together to the target. Prepare a trusted private config directory containing `wg.conf` in native WireGuard format and `local.env` based on the example. Review all values and root-executed code. Do not put actual keys or local settings in Git.
4. Run `sudo bash tor-client.sh setup PATH_TO_TRUSTED_CONFIG`. This installs root-owned private configuration and command files, without changing routes.

## Tested Ubuntu instance

The client command is installed. Session state is operator-controlled; use status and the rollback timer to determine whether a trial is currently active.

```bash
sudo kurukshetra-tor connect
sudo kurukshetra-tor status
```

Connect starts a 15-minute trial timer. Verify a fresh host-only SSH connection and Tor egress before confirming:

```bash
curl --max-time 35 https://check.torproject.org/api/ip
sudo kurukshetra-tor confirm
```

Confirm cancels the rollback timer for this running session only. This does not enable Tor isolation at boot. Reboot restores normal networking. Do not assume reboot remains private. Automatic startup is a separate, unimplemented feature.

```bash
sudo kurukshetra-tor disconnect
```

Disconnect deliberately restores ordinary direct networking. An expired trial timer does the same. During a confirmed session, tunnel/gateway failure should leave egress blocked until explicit disconnect; only tested cases are listed below.

## Verification evidence and limits

- Corrected conntrack ordering preserved host-only SSH.
- Gateway DNS resolved a public name; official Tor HTTPS check returned IsTor=true.
- Direct IPv6 HTTPS attempt timed out under the trial policy.
- Stopping the Pi gateway blocked an Ubuntu outbound request while SSH remained reachable; the Pi gateway was restarted.
- Reusable setup, connect, status, confirm and disconnect commands were exercised. Baseline routes and normal HTTPS were restored.
- A benign Tor Project onion URL discovered from its HTTPS headers timed out. Onion reachability remains unverified.
- Broader DNS/UDP leak tests, tunnel-interface deletion, boot persistence and Windows remain pending. This is a tested prototype, not a complete anonymity assessment.
- The egress policy intentionally restricts guest application traffic and guest Docker forwarding. Local services other than the explicit SSH recovery exception are unavailable during a session.

## Recovery

Use the Fusion console and the root-owned rollback script printed by the trial if SSH is interrupted. Keep the VM snapshot. Do not flush Docker tables or all firewall rules. Original Docker firewall tables are preserved. Per-trial backup directories are private under /root.

## Source update awaiting guest rollout

The repository source now supports unique client tunnel addresses and serializes session changes with `flock`. Generated rollback scripts check their session generation before removing routes or firewall state, so an old timer cannot undo a newer managed session. This protects cooperating script operations; it does not protect against unrelated root networking changes.

The installed Ubuntu client remains the previously tested first-peer version until explicitly updated. Do not describe repository changes as installed or live-tested. Existing sessions should be disconnected with their existing installed rollback before upgrading; keep the Fusion console available. New source requires `flock` (provided by Ubuntu's util-linux).

Trial expiry still deliberately restores ordinary direct Internet, as do disconnect and reboot. A confirmed session is not boot-persistent.

## Post-dashboard Ubuntu recheck

Read-only checks during an operator-started trial confirmed official HTTPS Tor verification, DNS on torwg0, Internet destination routing through the tunnel policy table, IPv6 request timeout, and continuing host-only SSH. The installed controller differs from the current repository source; these observations do not validate installing the latest downloadable client. No timer was confirmed or cancelled, no gateway outage was induced, and Windows/snapshots were untouched. Complete current-source rollout and its controlled verification before claiming the public installer fully verified.
