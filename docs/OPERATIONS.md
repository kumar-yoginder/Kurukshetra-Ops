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

## Entry points

`deploy.sh` and `setup.sh` remain root entry points. Setup prepares directories and permissions using sudo; it does not start services. Configure private `.env` before deployment. Monitoring placeholders need replacement before enabling that optional profile.

DNS maintenance lives in `scripts/dns/dns-toggle.sh`; dashboard initialization lives in `scripts/monitoring/init-dashboards.sh`. The former root wrappers have been removed; invoke the feature scripts directly. DNS recovery changes host resolver settings and restarts Docker. Dashboard initialization requires the optional monitoring stack. Neither runs during ordinary deployment.
