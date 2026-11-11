# Operations

Run production commands on the Pi from the repository root. Start with [architecture](ARCHITECTURE.md), [data flow](networking/DATA-FLOW.md), and [authentication](security/AUTHENTICATION.md) if the service boundaries are unfamiliar.

## Prepare private configuration

- Keep the stable site address and existing Pi-hole password in ignored `.env`. Deployment does not discover or rewrite addresses.
- Provision a leaf certificate covering the configured gateway hostname and establish client trust in the local CA. Do not regenerate the CA for a normal deployment. Nginx mounts only its leaf certificate/key.
- Prepare centralized identity using the local gateway bootstrap and an existing monitoring Python environment with the pinned Pydantic dependencies. Enter the password only at the hidden local prompts. The helper refuses to overwrite existing identities/encryption keys; preserve them during updates.
- The inventory profile needs private router settings, an approved certificate pin and guest credentials entered through `configure-router-secrets.py`. Do not pass a password in CLI arguments or commit generated settings.
- The Tor profile needs the separately provisioned private WireGuard configuration and selected bind address. Never distribute a peer’s private profile through the portal.

Gateway and inventory bootstrap, secret-file boundaries and lifecycle caveats are detailed in [gateway operations](security/GATEWAY.md) and [private inventory](networking/PRIVATE-INVENTORY.md). File-backed Compose secrets are not an encrypted vault.

## Deploy an already provisioned stack

```bash
./deploy.sh --gateway --tor --inventory --prepare --configure-only
./deploy.sh --gateway --tor --inventory up -d --build
./deploy.sh --gateway --tor --inventory ps
./deploy.sh --gateway --tor --inventory logs --tail 30
```

One Compose file defines all services. Pi-hole starts by default; gateway, Tor, inventory, observability and monitoring use opt-in profiles. Profiles select what starts, not what stops. The bot is managed by its separate Compose project. `--prepare` creates missing runtime paths and a regular Pi-hole log file; it does not reset ownership or change host networking. There is no automatic address discovery or recursive permission repair.

| Task | Command / guide |
| --- | --- |
| Validate selected stack | `./deploy.sh --gateway --tor --inventory config --quiet` |
| List every profile | `docker compose --profile "*" ps -a` |
| Restart Pi-hole only | `docker compose restart pihole` |
| Stop inventory collection | `docker compose stop router-inventory` |
| Stop Tor gateway | `docker compose stop tor-gateway` |
| Stop the full project | `docker compose --profile "*" stop` |
| Enable optional monitoring | Configure it first, then `./deploy.sh --gateway --monitoring up -d` |
| DNS recovery utility | `scripts/dns/dns-toggle.sh`; changes resolver settings/restarts Docker |
| Optional dashboard initialization | `scripts/monitoring/init-dashboards.sh` |

Do not remove central authorization to repair an unavailable backend. A stopped backend returns unavailable rather than becoming publicly accessible. Optional monitoring has separate setup/resource requirements and has not been validated in every gateway checkpoint.

## Web access and health

Use the configured canonical HTTPS hostname. A single central session gates the portal, Pi-hole, inventory JSON, snapshots, client downloads and monitoring routes. HTTP 80 is closed, not redirected. Direct IP web access is rejected. Identity, inventory, WAF and session-bridge listeners have no published host web port. DNS 53, SSH and WireGuard UDP 51820 remain necessary non-web protocols.

The former standalone inventory page and its HTML/CSS/JavaScript are removed. The main portal consumes the retained authenticated JSON feed. The former loopback inventory forwarding workflow is retired. Current topology and controls are documented in [architecture](ARCHITECTURE.md) and [gateway security](security/GATEWAY.md).

A container that is running without a health check is shown as running, not healthy. A DHCP lease is not proof of current device presence, and a WireGuard handshake is not a continuous connection guarantee. Certificate generation is a lifecycle job and need not run continuously. Consult [validation limits](security/GATEWAY.md) rather than treating all green container statuses as end-to-end proof.

## Collection schedules and freshness

| Producer | Normal cadence | Published data |
| --- | --- | --- |
| Host status/DNS job | Every minute | Allowlisted service state, anonymous DNS totals, separate private DNS counters |
| Inventory container | Every minute with failure backoff | Private router observations and 24-hour history |
| Host home/Tor probe | Every 15 minutes | Separate bounded download/upload/HTTPS-response samples |
| Portal | Every 30 seconds while visible | Reads saved data; does not start probes |

The status cron marker remains `kurukshetra-public-status` for compatibility; its name does not mean the endpoint is public. The Tor cron marker remains `kurukshetra-tor-metrics`, and that job now samples both the direct Pi uplink and Tor. Do not install duplicate host and container inventory schedules. Remove only the relevant marked entry in `crontab -e` when retiring a host schedule.

Router authentication renews automatically from locally mounted guest credentials. Rejected credentials pause retries until the secret changes; network errors back off. Certificate mismatch fails closed. The portal labels failed or old data stale rather than inventing current state. Saved JSON uses two-space indentation, Unicode and a trailing newline, with atomic publication and private permissions where needed.

See [data flow](networking/DATA-FLOW.md) and [speed methodology](networking/CONNECTION-SPEED.md) for caps, attribution limits and failure states.

## Images, layout and storage

Own images currently use CalVer tags: Nginx/session bridge `2026.11.09`, inventory `2026.11.11`, Tor `2026.10.23.2`. Check `docker-compose.yml` for the authoritative tags/digests. Vendor image references vary: some are pinned by digest, while other existing definitions still use upstream tags. Updating an image is a reviewed deployment change, not part of a documentation refresh.

- `config/`: templates, safe examples and canonical UI assets. Generated site settings are ignored.
- `containers/`: custom image sources.
- `scripts/`: operations grouped by feature, plus a synthetic documentation preview.
- `docs/`: architecture, security, networking, UI and approved screenshots.
- `certs/`, `data/`, `logs/`, `backups/`: local runtime material. Private contents stay outside Git.
- Implementation plans remain local and ignored.

Pi-hole retains its existing bind-mounted runtime data. Elasticsearch uses a Compose-managed volume when the monitoring profile starts; it does not require host `data/es_data` ownership repair. Identity state must be backed up together with its storage encryption key to a private destination. Inventory observations are pruned to a rolling 24 hours; this is not a permanent device audit trail.

Host Ethernet/Wi-Fi recovery is a separate systemd service, outside Compose. See [recovery](networking/WIFI-SSH-RECOVERY.md) before changing interfaces. Temporary diagnostic sudo access was removed after gateway verification; do not assume it is still available.

## Client sources and downloads

Canonical client sources live in `scripts/tor-client/ubuntu/` and `scripts/tor-client/windows/`. `publish-downloads.py` atomically publishes an explicit script allowlist and checksums under the generated web snapshot directory. Private profiles/keys are never included. Downloads now require the central session.

Deployment startup/preparation and status-schedule setup call the publisher. After a source-only change, run `python3 scripts/tor-client/publish-downloads.py` if not deploying. Installed guest files are independent until explicitly updated. Platform support and test limits are in the [Ubuntu](networking/UBUNTU-TOR-CLIENT.md) and [Windows](networking/WINDOWS-TOR-CLIENT.md) guides.

## Documentation captures

Use only the loopback synthetic preview documented in [screenshot workflow](ui/SCREENSHOTS.md). The preview does not read production data or secrets, and must never be deployed as an unauthenticated production route. No production service restart is needed to edit Markdown or update approved screenshots.

## Metrics observability

The deployed metrics-only `observability` profile is separate from the legacy `monitoring` profile. Grafana shares the central login under `/grafana/`; Prometheus and Alloy stay internal. Host and anonymous Chitragupt aggregates refresh every minute. See [observability operations](observability/README.md) for provisioning, limits, verification and safe stop commands. Raw logs, traces and real bot OTLP instrumentation are not enabled.

## Operational log events

Select Logs in the portal for sanitized categories from the existing minute job. This adds no container or database. The bounded snapshot retains up to 24 hours / 2,000 events; raw messages remain local. See [log viewer limits and maintenance](observability/LOGS.md).
