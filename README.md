# Current operations

See [operations](docs/OPERATIONS.md) for startup commands, image versions and layout.

# Kurukshetra-Ops

## Host security and implementation plans

Host hardening tools live in `scripts/host-hardening/`, examples in
`config/host-hardening/`, and usage/recovery instructions in
[Host hardening](docs/security/HOST-HARDENING.md). Actual site settings, firewall
rules and audit reports remain ignored. Review the guide before running any
privileged script; deployment does not automatically apply host hardening.

The Tor gateway is deployed; Ubuntu Server on VMware Fusion was the first test client. See the networking guides for supported commands and remaining validation limits.

## Deployment configuration

Keep the stable Ethernet address and password in ignored `.env` as `PIHOLE_LAN_IP` and `PIHOLE_API_PASSWORD`. Deployment validates existing configuration; it never discovers or rewrites addresses. Tor additionally needs its private WireGuard configuration and an appropriate `TOR_BIND_IP`.

```sh
./deploy.sh --gateway --tor --prepare --configure-only
./deploy.sh --gateway --tor up -d --build
./deploy.sh --gateway --tor ps
```

Use `--prepare` for missing runtime mount paths only. It does not reset ownership or change host networking. Reserve the Pi address in router DHCP settings. `ADDITIONAL_DNS_HOSTS` supplies optional local aliases. Docker internal DNS remains separate. See [operations](docs/OPERATIONS.md) for profile selection and maintenance utilities.

## Running services independently

Run commands from your project directory.
Pi-hole is the only default service. Other services are optional.

| Goal | Command |
| --- | --- |
| Start Pi-hole only on a stopped stack | `docker compose up -d` |
| Start Pi-hole and HTTPS gateway | `docker compose --profile gateway up -d` |
| Start Pi-hole and monitoring | `docker compose --profile monitoring up -d` |
| Start all services | `docker compose --profile gateway --profile monitoring up -d` |
| Start Elasticsearch alone | `docker compose up -d elasticsearch` |
| Start Kibana with required Elasticsearch | `docker compose up -d kibana` |
| Stop monitoring only | `docker compose stop filebeat kibana elasticsearch` |
| Stop gateway only | `docker compose stop nginx cert-gen` |
| Restart only Pi-hole | `docker compose restart pihole` |
| Show all containers | `docker compose --profile "*" ps -a` |
| Stop whole project | `docker compose --profile "*" stop` |

Profiles select what starts; they do not stop existing containers.
To switch to DNS only:
```sh
docker compose stop filebeat kibana elasticsearch nginx cert-gen
docker compose up -d pihole
```

The HTTPS dashboard requires Nginx; DNS-only mode still filters port 53.
Nginx tolerates stopped backends; their routes return 502 until they start.
Kibana and Filebeat require Elasticsearch. Starting either includes that dependency.
Stopping Elasticsearch interrupts their monitoring functionality.
Use `up -d SERVICE` to start a service and dependencies; `stop SERVICE` stops it.
Monitoring definitions are restored at their existing version 8.10.2;
this change does not upgrade or start them.
Older full-stack instructions below require the corresponding profiles.


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
- At least 4GB RAM for Elasticsearch + Kibana

### Pre-Deployment Configuration

**Review and update these variables in `docker-compose.yml` before deploying:**

| Service | Variable | Current Value | Notes |
|---------|----------|---------------|-------|
| **pihole** | `TZ` | `Asia/Kolkata` | Change to your timezone |
| **pihole** | `FTLCONF_webserver_api_password` | `password` | **MUST change** for security |
| **pihole** | `FTLCONF_dns_hosts` | `Detected host IP for dwarka.gateway; additional hosts configured in .env` | Update with your actual IPs/hostnames |
| **pihole** | `INTERFACE` | `eth0` | Verify your network interface |
| **elasticsearch** | `ES_JAVA_OPTS` | `-Xms1g -Xmx1g` | Adjust heap based on available RAM |
| **kibana** | `xpack.security.encryptionKey` | `something_at_least_32_chars...` | Change to random 32+ char string |
| **kibana** | `xpack.encryptedSavedObjects.encryptionKey` | `something_at_least_32_chars...` | Change to random 32+ char string |
| **kibana** | `xpack.reporting.encryptionKey` | `something_at_least_32_chars...` | Change to random 32+ char string |
| **kibana** | `SERVER_PUBLICBASEURL` | `https://dwarka.gateway/kibana` | Update to your domain |

### Fixed & Pre-Configured

✅ **Automatically handled — no changes needed:**
- **TLS Certificates** — Auto-generated by `cert-gen` service on first run
- **Directory Structure** — All data/log directories created with proper permissions
- **Service Dependencies** — Nginx waits for cert-gen, Filebeat waits for Elasticsearch
- **Health Checks** — All services monitored with configured health checks
- **Resource Limits** — Memory caps set to prevent resource exhaustion
- **Restart Policies** — Auto-restart on failure (except cert-gen)
- **Docker Network** — Internal network `kurukshetra-ops_default` created automatically
- **Elasticsearch Security** — xpack.security disabled for simplicity (enable in production)

### Installation & Setup

1. **Clone and navigate:**
   ```bash
   git clone https://github.com/kumar-yoginder/Kurukshetra-Ops.git
   cd Kurukshetra-Ops
   ```

2. **Edit `docker-compose.yml` — Update required variables (see table above):**
   ```bash
   nano docker-compose.yml
   ```

3. **Automated Setup (⚠️ Recommended):**
   Run the setup script to automatically fix all permissions and validate configuration:
   ```bash
   ./deploy.sh --prepare --configure-only
   ```
   This script:
   - ✅ Creates all required directories (`certs/`, `data/`, `logs/`)
   - ✅ Fixes Elasticsearch data directory ownership (UID 1000)
   - ✅ Sets proper permissions for certificates, logs, and data volumes
   - ✅ Creates `pihole.log` file (required for docker volume mount)
   - ✅ Validates `docker-compose.yml` for required changes
   - ✅ Provides pre-flight checklist

   **Or manually set permissions:**
   ```bash
   sudo chown 1000:1000 data/es_data/
   ```
   - ⚠️ **Critical:** Elasticsearch container runs as user 1000
   - Without this, Elasticsearch will fail with permission denied errors

4. **Start services:**
   ```bash
   docker compose up -d
   ```
   - Directories and permissions are pre-configured
   - Certificates auto-generated on first run
   - All services wait for health checks before starting

4. **Verify services:**
   ```bash
   docker compose ps
   ```

6. **Initialize Dashboards & Pipelines (Optional but Recommended):**
   After services are healthy, load Kibana dashboards and create the Pi-hole ingest pipeline:
   ```bash
   ./scripts/monitoring/init-dashboards.sh
   ```
   This script:
   - ✅ Loads pre-built Nginx dashboards
   - ✅ Creates custom Pi-hole log parser pipeline (ECS-compliant)
   - ✅ Configures Filebeat index rollover for index lifecycle management
   - ✅ Validates setup completion

   **Or run commands manually (via Nginx proxy):**
   ```bash
   # Load Nginx dashboards
   docker exec -it filebeat filebeat setup --dashboards

   # Create Pi-hole ingest pipeline (via Nginx proxy)
   curl -sk -X PUT "https://localhost/elastic/_ingest/pipeline/pihole-pipeline" \
     -H 'Content-Type: application/json' \
     -d '{
       "description": "Pi-hole log parser",
       "processors": [{
         "grok": {
           "field": "message",
           "patterns": ["%{SYSLOGTIMESTAMP:timestamp} %{DATA:process}\\[%{NUMBER:pid}\\]: %{WORD:action} %{IPORHOST:domain} is %{IP:ip}"],
           "ignore_missing": true
         }
       }]
     }'
   ```

7. **Access services:**
   Since only ports 80/443 are exposed, all services are accessed through the Nginx reverse proxy:
   
   - **Nginx Home:** `https://localhost` (self-signed certificate)
   - **Pi-hole DNS Admin:** `https://localhost/admin`
   - **Kibana Dashboards:** `https://localhost/kibana`
   - **Elasticsearch API:** `https://localhost/elastic`

   **Note:** Self-signed certificates will show browser warnings — this is normal for local development.
   
   To bypass SSL warnings in curl:
   ```bash
   curl -sk https://localhost/elastic/_cluster/health
   curl -sk https://localhost/kibana/api/status
   ```

8. **Stop services:**
   ```bash
   docker compose down
   ```

## 📁 Project Structure

```
Kurukshetra-Ops/
├── docker-compose.yml          # Service definitions & orchestration
├── dns-toggle.sh               # DNS management utility
├── docs/REPOSITORY-HYGIENE.md              # Security & operations guidelines
├── README.md                   # This file
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
- **Directory:** `certs/` created and configured by setup script
- **⚠️ Important:** Private keys in `certs/` are excluded from git (see `.gitignore`)
- **Lifecycle:** Runs once on first `docker compose up`, then stays in standby

### pihole
DNS sinkhole and ad blocker with web admin interface
- **Port:** 53/UDP (DNS), 80/TCP (web UI)
- **Admin URL:** `http://localhost/admin`
- **Memory Limit:** 256MB
- **⚠️ Requires Configuration:**
  - Change `FTLCONF_webserver_api_password` from `password`
  - Update `FTLCONF_dns_hosts` with your network IPs/hostnames
  - Verify `INTERFACE` matches your system (default: `eth0`)
  - Adjust `TZ` to your timezone

### nginx
High-performance reverse proxy and web server
- **Port:** 80/443 (HTTP/HTTPS)
- **Memory Limit:** 128MB
- **Features:** SSL/TLS termination, load balancing, static content
- **SSL/TLS:** Uses auto-generated certificates from `cert-gen`
- **Config:** `config/nginx/conf.d/default.conf`

### filebeat
Log shipper for centralized log collection
- **Input Sources:** Docker container logs, Nginx logs, Pi-hole logs
- **Output:** Elasticsearch
- **Memory Limit:** 150MB
- **Depends On:** Elasticsearch (waits for health check)

### elasticsearch
Search & analytics engine for log data storage
- **Port:** 9200 (HTTP API)
- **Memory Limit:** 2GB
- **Heap Size:** Configurable via `ES_JAVA_OPTS` (default: 1GB)
- **Storage:** `data/es_data/` (persistent, not version-controlled)
- **⚠️ Production Note:** Security disabled by default (`xpack.security.enabled=false`)

### kibana
Visualization and analytics UI for Elasticsearch
- **Port:** 5601 (internal), exposed via Nginx at `/kibana`
- **Memory Limit:** 1500MB
- **Node Max Memory:** 1GB
- **⚠️ Requires Configuration:**
  - Change all `xpack.*` encryption keys to random 32+ char strings
  - Update `SERVER_PUBLICBASEURL` to your domain
- **Depends On:** Elasticsearch (waits for health check)

## 🌐 Network Architecture

**Single Entry Point via Nginx:**

Only ports **80** and **443** are exposed to the host. All services are accessed through the Nginx reverse proxy:

```
┌─────────────────────────────────────┐
│         Host (Your Machine)         │
│   Port 80 (HTTP)                    │
│   Port 443 (HTTPS/SSL)              │
└──────────────┬──────────────────────┘
               │
      ┌────────▼─────────┐
      │   Nginx Gateway  │
      │ (Reverse Proxy)  │
      └────────┬─────────┘
               │
    ┌──────────┼──────────┬──────────┬──────────┐
    │          │          │          │          │
    ▼          ▼          ▼          ▼          ▼
  Pi-hole    Kibana  Elasticsearch  Nginx   Static
  /admin     /kibana   /elastic     status   Content
```

**Service Routing:**

| Service | Internal Port | Nginx Path | Access |
|---------|---------------|-----------|--------|
| Pi-hole Admin | 80 | `/admin/` | `https://localhost/admin` |
| Pi-hole API | 80 | `/api/` | `https://localhost/api/` |
| Kibana | 5601 | `/kibana/` | `https://localhost/kibana` |
| Elasticsearch | 9200 | `/elastic/` | `https://localhost/elastic` |
| Nginx Status | — | `/nginx_status` | `https://localhost/nginx_status` |

**Benefits:**
- ✅ Single SSL/TLS certificate for all services
- ✅ Services not directly exposed to network
- ✅ Centralized logging via Nginx
- ✅ Easy to add new services
- ✅ Better security posture

## 🔐 Network & Security

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

- **[docs/REPOSITORY-HYGIENE.md](docs/REPOSITORY-HYGIENE.md)** — Complete security, hygiene, and operations guidelines
- **[docker-compose.yml](docker-compose.yml)** — Service configurations and deployment specs
- **[dns-toggle.sh](dns-toggle.sh)** — DNS management utility
- **[deploy.sh](deploy.sh)** — Deployment and explicit first-time preparation
- **[init-dashboards.sh](init-dashboards.sh)** — Post-deployment dashboard & pipeline initialization

## 🤝 Contributing

1. Never commit secrets, keys, or `.env`
2. Keep runtime data on local systems only
3. Test changes with `docker compose up` before committing
4. Follow guidelines in [docs/REPOSITORY-HYGIENE.md](docs/REPOSITORY-HYGIENE.md)

## � Troubleshooting

### Elasticsearch fails to start with permission errors
```
permission denied
docker.io/library/elasticsearch:8.10.2: chown: data/es_data: permission denied
```
**Solution:** Run the setup script or manually fix permissions:
```bash
sudo chown 1000:1000 data/es_data/
```

### Elasticsearch runs out of memory
Increase heap size in `docker-compose.yml`:
```yaml
elasticsearch:
  environment:
    - ES_JAVA_OPTS=-Xms2g -Xmx2g  # Adjust as needed
```

### Pi-hole DNS not working
1. Verify `FTLCONF_dns_hosts` is correctly set in `docker-compose.yml`
2. Check network interface (`INTERFACE`): `ip addr`
3. Restart Pi-hole: `docker compose restart pihole`

### Kibana cannot connect to Elasticsearch
1. Check Elasticsearch is healthy: `docker compose logs elasticsearch`
2. Verify service name resolution: `docker compose exec kibana ping elasticsearch`
3. Ensure Elasticsearch finished startup: `docker compose logs -f elasticsearch`

### Certificate errors in Nginx
1. Check cert generation: `docker compose logs cert-gen`
2. Verify certificates exist: `ls -la certs/`
3. Restart Nginx: `docker compose restart nginx`

### View logs for any service
```bash
docker compose logs -f <service-name>
# Examples:
docker compose logs -f elasticsearch
docker compose logs -f pihole
docker compose logs -f nginx
```

## �📄 License

Internal use only.

---

**Repository:** [github.com/kumar-yoginder/Kurukshetra-Ops](https://github.com/kumar-yoginder/Kurukshetra-Ops)

## Pi-hole blocklists and automatic refresh

Compose uses `config/pihole/bootstrap.sh` to seed a fresh Pi-hole database from
`config/pihole/adlists.list` (StevenBlack, HaGeZi PRO, and HaGeZi TIF). Existing
databases retain their lists and group assignments; edit those through the UI.
The existing `./data/pihole` volume preserves the database across recreation.
The startup wrapper changes Pi-hole's built-in Gravity cron job to daily at
03:47 Asia/Kolkata and retains its other jobs. No host cron job is needed.
`docker compose up -d` applies this configuration on the next recreation.

## Optional Tor gateway prototype

The Tor gateway is an optional profile in the main Compose file. See
[the Tor gateway guide](docs/networking/TOR-GATEWAY.md) and the implementation
plan for its current validation state. Do not attach privacy-sensitive clients
before guest egress restrictions and failure tests pass.

## Emergency Wi-Fi maintenance path

Ethernet remains the permanent Pi link. An optional Wi-Fi recovery monitor is
being prepared to provide local SSH access through Wi-Fi when Ethernet loses
its link or repeatedly cannot reach the router. See
transparent failover for services bound to the Ethernet address; the recovery
service is not installed or enabled yet.

## Review plans


These are reviewed proposals and inventories, not evidence of file/network removal.
