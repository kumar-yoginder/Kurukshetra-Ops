# Optional Pi-hosted Tor client gateway

## Current state

Gateway deployed and bootstrapped; one Ubuntu peer was provisioned and a reversible live trial tested. Ubuntu has since been disconnected intentionally. Peer keys remain outside Git. Do not treat this prototype as an anonymity guarantee or a verified fail-closed setup.

## Layout

- `docker-compose.yml`: main Compose file with optional `tor` profile.
- `containers/tor-gateway/`: official Debian base, distribution Tor/WireGuard/nftables packages, configuration and health check.
- `config/tor-gateway/wg0.conf.example`: placeholder server peer configuration. Real `wg0.conf` and client exports are ignored.
- Tor state resides in a private Docker volume; never export its cookie or state into Git.

The single gateway container uses a separate Docker bridge and its own network namespace, not host networking. It shares neither Pi-hole's network nor its DNS service configuration. The Pi's existing LAN address will publish UDP 51820 after review. The safe default binds only loopback; set `TOR_BIND_IP` in ignored `.env` only for the intended host address. LAN binding alone is not a source firewall: review upstream port forwarding and the host ingress policy before exposure.

## Traffic design

Guest WireGuard -> container wg0 -> Tor TCP transparent port and UDP DNS port -> Tor network. There is no direct packet forwarding or client NAT fallback. Direct access to private IPv4 destinations is blocked, except Tor's virtual onion mapping range. Unsupported UDP and client IPv6 are blocked. Tor's own bootstrap resolver traffic can use ordinary DNS; this is distinct from client destination lookups.

Internal tunnel proposal is `10.77.0.0/24`; first peer `10.77.0.2/32`. Tor onion virtual addresses use `10.192.0.0/10`. Confirm no overlap on the Mac, guest, Pi or reachable lab networks before use. These are proposed internal defaults, not discovered private site values. Use one /32 AllowedIPs assignment per peer; do not accept client routes to other peers/subnets.

Tor DNS supports a restricted set of records, not a full recursive DNS service. This prototype supports UDP DNS mapping; TCP DNS is explicitly blocked. Applications using QUIC, arbitrary UDP, unusual DNS record types, or direct LAN services may fail. Onion access must be tested with a benign service and an application that supports the resulting connection flow. A regular browser is not equivalent to Tor Browser.

## Startup and review gates

1. Finish the pre-change VM snapshot; verify recovery access and route/subnet conflicts.
2. Review container policies and build/static checks. Generate server/client keys securely later; do not print private keys.
3. Populate ignored server configuration, verify key-file permissions and bind address.
4. Start the gateway only after this phase is reviewed:

```bash
docker compose -f docker-compose.yml --profile tor up -d --no-deps tor-gateway
```

5. Observe Tor bootstrap and health before attaching any peer. Health checks report readiness; an unhealthy status alone does not restart a Docker container.
6. Configure the test Ubuntu guest's kill switch and explicit host-only SSH recovery exception before allowing general Internet traffic. Tunnel defaults alone are insufficient. Test IPv4, IPv6, DNS, UDP and tunnel/Tor outages.

## Non-deploying checks

```bash
docker compose -f docker-compose.yml --profile tor config --quiet
docker compose -f docker-compose.yml --profile tor build tor-gateway
docker run --rm --network none --entrypoint tor kurukshetra/tor-gateway:2026.10.23 --verify-config -f /etc/tor/torrc
```

The entrypoint installs namespace firewall rules before creating the tunnel, then starts Tor as its unprivileged distribution account. No public SOCKS, Tor relay, control port or TCP proxy port is published. NET_ADMIN is scoped to the container namespace; no SYS_ADMIN, privileged mode or Docker socket mount is used. Runtime configuration and the image remain trusted code and require review.

## Stop and recovery

Stop only the gateway:

```bash
docker compose -f docker-compose.yml --profile tor stop tor-gateway
```

Do not run whole-project `down` or flush host firewall rules as a rollback. Existing Pi-hole/Nginx services must remain running. A properly configured guest should lose Internet access when this service is stopped. Restore guest networking only deliberately using its recorded baseline and recovery path. Retain peer keys/Tor state unless explicitly retiring the service; deleting them is not routine cleanup.

## Current checkpoint and remaining work

The Pi gateway is deployed, bootstrapped fully and reports healthy. One Ubuntu peer was provisioned; temporary and reusable manual sessions passed DNS and official Tor HTTPS checks. Stopping the gateway blocked a test request while host-only SSH remained available. Ubuntu was deliberately disconnected after testing and now uses ordinary networking.

Onion reachability remains unverified after a timeout. Tor-process-only failure, tunnel-interface deletion, restart persistence, packet-observed DNS/UDP/IPv6 behavior and broader compatibility checks remain open. Client address generalization and session locking are being refined in source; the installed tested Ubuntu command still uses its existing first-peer setup. No automatic guest isolation at boot is provided. Temporary diagnostic sudo revocation remains deferred to final cleanup by user instruction.

Sources: https://manpages.debian.org/trixie/tor/tor.1.en.html and https://www.wireguard.com/quickstart/

See [Ubuntu client commands](UBUNTU-TOR-CLIENT.md) for tested session behavior and remaining checks.
