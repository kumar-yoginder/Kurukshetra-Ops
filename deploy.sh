#!/usr/bin/env bash
# Pi-side entry point. Does not manage host networking or guest clients.
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
usage() {
    cat <<'HELP'
Usage: ./deploy.sh [--gateway] [--tor] [--inventory] [--prepare] [COMPOSE COMMAND...]
Default: Pi-hole only, up -d. --tor enables the Tor profile.
--gateway enables HTTPS gateway and certificate services.
--monitoring enables Elasticsearch, Filebeat and Kibana (configure them first).
--inventory enables the private router collector (configure guest secrets first).
--prepare creates missing runtime mount paths without changing existing ownership.
--configure-only validates configuration without starting services.
Examples:
  ./deploy.sh --gateway --tor config --quiet
  ./deploy.sh --gateway --tor up -d --build
  ./deploy.sh --gateway --tor ps
  ./deploy.sh --gateway --tor logs --tail 50
Private .env must contain PIHOLE_LAN_IP and PIHOLE_API_PASSWORD.
HELP
}
compose=(docker compose -f docker-compose.yml)
profiles=()
prepare=false
validate_only=false
tor=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --gateway) profiles+=(--profile gateway); shift ;;
        --monitoring) profiles+=(--profile monitoring); shift ;;
        --inventory) profiles+=(--profile inventory); shift ;;
        --tor) tor=true; profiles+=(--profile tor); shift ;;
        --prepare) prepare=true; shift ;;
        --configure-only) validate_only=true; shift ;;
        --help|-h) usage; exit 0 ;;
        *) break ;;
    esac
done
compose+=("${profiles[@]}")
# Compose validates required variables without printing their values.
"${compose[@]}" config --quiet
if "$tor" && [[ ! -f config/tor-gateway/wg0.conf ]]; then
    echo "Missing private config/tor-gateway/wg0.conf; provision the gateway first." >&2
    exit 1
fi
if "$prepare"; then
    mkdir -p data/pihole logs/pihole logs/nginx certs
    if [[ -d logs/pihole/pihole.log ]]; then
        echo "logs/pihole/pihole.log must be a file, not a directory." >&2
        exit 1
    fi
    if [[ ! -e logs/pihole/pihole.log ]]; then
        (umask 022; touch logs/pihole/pihole.log)
    fi
fi
if "$prepare" || { ! "$validate_only" && [[ "${1:-up}" == up ]]; }; then
    python3 scripts/tor-client/publish-downloads.py
fi
if "$validate_only"; then exit 0; fi
if [[ $# -eq 0 ]]; then set -- up -d; fi
exec "${compose[@]}" "$@"
