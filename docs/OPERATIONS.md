# Operations

Run commands on the Pi from the repository root.

## Start the deployed stack

```sh
docker compose -f docker-compose.yml --profile gateway --profile tor up -d --build
```

This starts Pi-hole, certificate management, Nginx and Tor. Monitoring is optional. The bot is managed by its separate Compose project.

## Images and layout

Project images use CalVer tags: `kurukshetra/nginx-gateway:2026.10.23` and `kurukshetra/tor-gateway:2026.10.23.2`. Nginx retains the previously deployed upstream digest. Vendor services keep upstream version tags.

- `config/`: service configuration and safe examples; site settings ignored.
- `containers/`: custom image sources.
- `scripts/`: host and guest operations grouped by feature.
- `docs/networking/` and `docs/security/`: operational guides.
- `certs/`, `data/`, `logs/`, `backups/`: local runtime material.
- Implementation plans stay local and excluded from Git.

The ignored `.env` supplies `PIHOLE_API_PASSWORD`, `PIHOLE_LAN_IP`, and `TOR_BIND_IP`. Existing credentials were preserved. Never commit keys or private settings.

Ethernet/Wi-Fi recovery runs as a separate host systemd service; Compose does not manage it. See [Wi-Fi recovery](networking/WIFI-SSH-RECOVERY.md), [Ubuntu client](networking/UBUNTU-TOR-CLIENT.md), and [host hardening](security/HOST-HARDENING.md).

## Single deployment entry point

`deploy.sh` replaces the separate setup script. It preserves private `.env` settings and existing file ownership. No automatic IP discovery or sudo is used.

For a fresh checkout, create private `.env` with `PIHOLE_LAN_IP` and `PIHOLE_API_PASSWORD`. Provision Tor keys separately before selecting Tor; `TOR_BIND_IP` controls its LAN endpoint. Never commit those files.

```sh
./deploy.sh --gateway --tor --prepare --configure-only
./deploy.sh --gateway --tor up -d --build
./deploy.sh --gateway --tor ps
./deploy.sh --gateway --tor logs --tail 50
```

`--prepare` creates only missing runtime directories and the Pi-hole log file. Existing root-owned paths are not changed. Permission problems need a specific operator fix, not recursive ownership resets. Without flags, deployment selects Pi-hole only. Flags precede the Compose command. `--configure-only` validates existing settings; it no longer discovers or writes addresses.

Monitoring remains optional: use explicit Compose monitoring profiles and follow its separate configuration requirements. Host network recovery and guest Tor setup remain separate utilities.

DNS maintenance lives in `scripts/dns/dns-toggle.sh`; dashboard initialization lives in `scripts/monitoring/init-dashboards.sh`. DNS recovery changes resolver settings and restarts Docker; neither maintenance utility runs during normal deployment.

All services are defined in one `docker-compose.yml`. Gateway, Tor and monitoring remain separate opt-in profiles. The former Tor overlay file has been removed.

## Runtime storage

The tracked `data/.gitkeep` retains the main data directory. Pi-hole keeps its existing ignored bind mount. Elasticsearch uses the Compose-managed `elasticsearch-data` named volume, created when the monitoring profile starts; no host Elasticsearch directory or ownership setup is required. The old host `data/es_data` contents are intentionally discarded at the operator request, not migrated.

Use `./deploy.sh --monitoring up -d` to select monitoring. `--prepare` remains necessary on first installation for the Pi-hole log-file bind mount; Compose cannot create that source as a regular file automatically.

## Public status page

The landing page shows only allowlisted service display names, basic container states and snapshot time. It publishes no image versions, IPs, ports, logs, environment, or credentials, and provides no management actions. Running without a health check is distinguished from healthy. Optional missing services display Not deployed.

Install the per-user minute collector using `python3 scripts/monitoring/install-status-refresh.py`. Existing unrelated cron jobs are preserved. The browser fetches the ignored generated `status.json` every 30 seconds and marks snapshots stale after three minutes. The collector uses the operator existing Docker access; no Docker socket is mounted into Nginx. No API backend or container restart is required. To remove the schedule, use `crontab -e` and delete only the line ending `# kurukshetra-public-status`.

## Public Tor details

The Tor card opens anonymous peer activity, setup commands and cached Tor path measurements. No peer keys, LAN endpoint addresses or tunnel addresses are published. Recent handshake is not a connected-device guarantee. A private per-device peer bundle remains required; setup is Ubuntu 24.04 only. Public client-script downloads are generated from reviewed source when installing refresh jobs.

`collect-tor-metrics.py` schedules a bounded 256 KiB HTTPS download through container-local SOCKS every 15 minutes. There is no public command endpoint and no direct-network fallback. Tor verification uses check.torproject.org; the sample uses Cloudflare speed-test download endpoint. Metrics can fail or time out. Sample throughput includes connection setup and is not maximum bandwidth. Probe exit IP may differ from clients or subsequent circuits. The SOCKS listener is loopback-only inside the Tor container, with no published port.

The details remain public at the operator request. mTLS is deferred and not enabled. Remove the `# kurukshetra-tor-metrics` cron line to stop probes.

Speed probe reference: [Cloudflare speed-test engine](https://github.com/cloudflare/speedtest/blob/main/README.md). This is a small sample, not its full methodology.

## Platform client sources and downloads

The single source of truth is `scripts/tor-client/ubuntu/` and `scripts/tor-client/windows/`. Ubuntu is named specifically because support is validated for Ubuntu 24.04, not all Linux distributions. `publish-downloads.py` atomically generates an explicit public-file allowlist under `config/nginx/www/client/ubuntu/` and `/windows/`, with SHA256SUMS. Private profiles, keys and session-test helpers are never published. Generated copies are ignored by Git.

Deployment startup/explicit preparation and status-schedule installation call the publisher. Run `python3 scripts/tor-client/publish-downloads.py` after a source-only edit if not deploying. Status and log commands do not republish. Cross-directory symlinks are unsuitable because Nginx mounts only its web directory. Existing installed guest files remain independent until explicitly updated.

Saved JSON uses two-space indentation, Unicode text, and a trailing newline. This applies to configuration and snapshots; private JSON remains ignored and owner-readable only.
