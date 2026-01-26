# Kurukshetra-Ops

Divine command operations orchestration platform. A complete ops stack for managing infrastructure, services, and monitoring using Docker, Elasticsearch, Pi-hole DNS, Nginx, and Filebeat.

## 🎯 Project Overview

**Kurukshetra-Ops** is an integrated DevOps platform that provides:

- **Certificate Management** — Automated TLS/SSL certificate generation via Docker
- **DNS Management** — Pi-hole for DNS filtering, blocking, and analytics
- **Web Gateway** — Nginx reverse proxy with SSL termination
- **Log Aggregation** — Filebeat for centralized log shipping
- **Elasticsearch** — Full-text search and analytics engine for log data
- **Service Orchestration** — Docker Compose for seamless deployment

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose installed
- Linux/macOS system with bash

### Installation & Setup

1. **Clone and navigate:**
   ```bash
   git clone https://github.com/kumar-yoginder/Kurukshetra-Ops.git
   cd Kurukshetra-Ops
   ```

2. **Start services:**
   ```bash
   docker compose up -d
   ```
   - Directories and permissions are pre-configured — ready to run immediately after git pull
   - Certificates are auto-generated on first run

3. **Verify services:**
   ```bash
   docker compose ps
   ```

4. **Access services:**
   - Nginx: `https://localhost`
   - Pi-hole Dashboard: `http://localhost:80/admin`
   - Elasticsearch: `http://localhost:9200`

5. **Stop services:**
   ```bash
   docker compose down
   ```

## 📁 Project Structure

```
Kurukshetra-Ops/
├── docker-compose.yml          # Service definitions & orchestration
├── dns-toggle.sh               # DNS management utility
├── instruction.md              # Security & operations guidelines
├── readme.md                   # This file
├── .gitignore                  # VCS ignore rules (keys, secrets, data)
├── certs/                      # TLS certificates (auto-generated, not committed)
├── config/                     # Service configurations
│   ├── filebeat/filebeat.yml   # Filebeat log shipper config
│   └── nginx/                  # Nginx configs & web root
│       ├── conf.d/             # Nginx virtual hosts
│       └── www/                # Static web content
├── data/                       # Runtime data volumes (not committed)
│   ├── es_data/               # Elasticsearch indices & cluster state
│   ├── pihole/                # Pi-hole database & configs
│   └── vscode/                # VS Code workspace data
└── logs/                       # Service logs (not committed)
    ├── nginx/                 # Nginx access & error logs
    └── pihole/                # Pi-hole query logs
```

## 🛠️ Services

### cert-gen
Automatically generates self-signed TLS certificates for Nginx on first run.
- **Uses:** Alpine Linux, OpenSSL
- **Output:** `certs/ca.key`, `certs/ca.crt`, `certs/server.key`, `certs/server.crt`

### pihole
DNS sinkhole and ad blocker
- **Port:** 53/UDP, 80/TCP (web interface)
- **Admin URL:** `http://localhost/admin`
- **Config:** Via environment variables in compose

### nginx
High-performance reverse proxy and web server
- **Port:** 80/443 (HTTP/HTTPS)
- **Features:** SSL/TLS termination, load balancing, static content

### filebeat
Log shipper for sending logs to Elasticsearch
- **Input:** Docker container logs
- **Output:** Elasticsearch indices

### elasticsearch
Search & analytics engine for centralized log storage
- **Port:** 9200 (HTTP API)
- **Storage:** `data/es_data/`

## 🔐 Security

For detailed security guidelines, permissions, and secret management, see **[instruction.md](instruction.md)**.

**Key practices:**
- Never commit private keys, certificates, or `.env` files
- All sensitive files excluded via `.gitignore`
- Runtime data volumes ignored from version control
- Use Docker secrets for production credentials
- Rotate exposed credentials immediately

## 📋 Typical Workflows

### Initialize fresh environment
```bash
git clone https://github.com/kumar-yoginder/Kurukshetra-Ops.git
cd Kurukshetra-Ops
docker compose up -d
```

### View logs
```bash
docker compose logs -f nginx
docker compose logs -f pihole
docker compose logs -f filebeat
```

### Backup Elasticsearch data
```bash
tar -czf backup-es-$(date +%F).tar.gz data/es_data/
```

### Restart a service
```bash
docker compose restart nginx
```

### Access service shell
```bash
docker compose exec pihole sh
docker compose exec elasticsearch sh
```

## 📚 Documentation

- **[instruction.md](instruction.md)** — Complete security, hygiene, and operations guidelines
- **[docker-compose.yml](docker-compose.yml)** — Service configurations and deployment specs
- **[dns-toggle.sh](dns-toggle.sh)** — DNS management utility

## 🤝 Contributing

1. Never commit secrets, keys, or `.env`
2. Keep runtime data on local systems only
3. Test changes with `docker compose up` before committing
4. Follow guidelines in [instruction.md](instruction.md)

## 📄 License

Internal use only.

---

**Repository:** [github.com/kumar-yoginder/Kurukshetra-Ops](https://github.com/kumar-yoginder/Kurukshetra-Ops)
