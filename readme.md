# Kurukshetra-Ops — README

## Overview
This repo orchestrates local services (cert generation, Pi-hole, etc.) and stores runtime data under `data/`. Large runtime files and secrets are intentionally ignored.

- Certs generator and service definitions: `docker-compose.yml`
- Large data directory: `data/es_data/`
- Local setup helper: `Note`

## Getting started (local dev)
1. Prepare directories and ownership:
   - Follow: `sudo mkdir -p data/es_data data/pihole data/vscode logs/nginx logs/pihole && sudo chown -R 1000:1000 data/ logs/` (see `Note`)
2. Generate certs (docker):
   - `docker compose up cert-gen` (uses `docker-compose.yml` cert-gen service)
   - Inspect generated certs in `certs/` and ensure private keys are NOT committed.
3. Start services:
   - `docker compose up -d`
4. Stop & cleanup:
   - `docker compose down`
   - Optional cleanup: `docker system prune -af` (use with caution)

## Security & hygiene (must-read)
- Never commit:
  - `certs/*.key`, `certs/*.csr`, `certs/*.srl` (covered in `.gitignore`)
  - `data/es_data/` and other runtime data
  - `.env`
- Rotate credentials immediately if accidentally exposed.
- Use secure secret management for production (Docker secrets, Vault).

## Maintenance tips
- Backup `data/es_data/` using ES snapshot APIs or `tar` for ad-hoc copies — do not version-control Lucene files.
- Rotate logs and prune old docker images.
- Periodically run the Sensitive Information Check from `instruction.md`.

## Directory Structure
```
.
├── docker-compose.yml          # Service definitions & cert-gen
├── dns-toggle.sh               # Utility script
├── certs/                      # Generated certificates (not committed)
├── config/                     # Service configurations
│   ├── filebeat/
│   └── nginx/
├── data/                       # Runtime data (not committed)
│   ├── es_data/               # Elasticsearch indices & snapshots
│   └── vscode/                # VS Code workspace data
├── logs/                       # Application logs
│   ├── nginx/
│   └── pihole/
├── instruction.md             # Security & hygiene guidelines
└── readme.md                   # This file
```

## Links
- [instruction.md](instruction.md) — Security & hygiene guidelines
- [docker-compose.yml](docker-compose.yml) — Service definitions
- [certs/](certs/) — Generated certificates directory
- [data/es_data/](data/es_data/) — Elasticsearch runtime data
- [logs/](logs/) — Application logs
