# Operations

Run commands on the Pi from the repository root.

## Start the deployed stack

```sh
docker compose -f docker-compose.yml -f docker-compose.tor.yml --profile gateway --profile tor up -d --build
```

This starts Pi-hole, certificate management, Nginx and Tor. Monitoring is optional. The bot is managed by its separate Compose project.

## Images and layout

Project images use CalVer tags: `kurukshetra/nginx-gateway:2026.10.23` and `kurukshetra/tor-gateway:2026.10.23`. Nginx retains the previously deployed upstream digest. Vendor services keep upstream version tags.

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
