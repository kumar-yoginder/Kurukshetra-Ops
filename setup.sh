#!/bin/bash

# Kurukshetra-Ops Setup Script
# Automates pre-deployment configuration and permissions

set -e

echo "=========================================="
echo "Kurukshetra-Ops Setup Script"
echo "=========================================="
echo ""

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then 
   echo "❌ This script must run with sudo for permission management"
   echo "   Run: sudo ./setup.sh"
   exit 1
fi

# Get the actual user (not root)
ACTUAL_USER="${SUDO_USER:-$(whoami)}"
if [ "$ACTUAL_USER" = "root" ]; then
    echo "⚠️  Warning: Running as root. Please run with sudo from a non-root user."
    exit 1
fi

echo "✓ Running as: $ACTUAL_USER"
echo ""

# Step 1: Fix directory permissions
echo "Step 1: Fixing directory permissions..."
echo ""

# Create directories if they don't exist
mkdir -p data/es_data
mkdir -p data/pihole
mkdir -p data/vscode
mkdir -p logs/nginx
mkdir -p logs/pihole
mkdir -p certs

# Set correct ownership for Elasticsearch (runs as UID 1000)
echo "  - Setting Elasticsearch data directory ownership (1000:1000)..."
chown 1000:1000 data/es_data/
chmod 755 data/es_data/

# Set permissions for certs directory (cert-gen service writes here)
echo "  - Setting certs directory permissions..."
chmod 755 certs/

# Set permissions for logs
echo "  - Setting logs directory permissions..."
chown -R 1000:1000 logs/nginx/
chown -R 1000:1000 logs/pihole/
chmod 755 logs/nginx/
chmod 755 logs/pihole/

# Create pihole.log file (docker volume mount requires file, not directory)
echo "  - Creating pihole.log file..."
touch logs/pihole/pihole.log
chown 1000:1000 logs/pihole/pihole.log
chmod 644 logs/pihole/pihole.log

# Set permissions for other data directories
echo "  - Setting Pi-hole data directory permissions..."
mkdir -p data/pihole
chmod 755 data/pihole/

echo "  - Setting VS Code data directory permissions..."
mkdir -p data/vscode
chmod 755 data/vscode/

echo "✓ Permissions fixed successfully"
echo ""

# Step 2: Check docker-compose.yml for required changes
echo "Step 2: Checking docker-compose.yml for required configurations..."
echo ""

CONFIG_CHECKS=(
    "FTLCONF_webserver_api_password=password"
    "xpack.security.encryptionKey=something_at_least_32"
)

NEEDS_CONFIG=false
for check in "${CONFIG_CHECKS[@]}"; do
    if grep -q "$check" docker-compose.yml; then
        echo "  ⚠️  Found placeholder: $check"
        NEEDS_CONFIG=true
    fi
done

if [ "$NEEDS_CONFIG" = true ]; then
    echo ""
    echo "⚠️  Action Required:"
    echo "   Edit docker-compose.yml and change:"
    echo "   - FTLCONF_webserver_api_password (change from 'password')"
    echo "   - FTLCONF_dns_hosts (update with your IPs/hostnames)"
    echo "   - xpack.* encryption keys (use random 32+ char strings)"
    echo ""
    read -p "Continue without editing? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Please edit docker-compose.yml manually, then run this script again."
        exit 1
    fi
fi

echo "✓ Configuration check complete"
echo ""

# Step 3: Summary
echo "=========================================="
echo "Setup Complete! ✓"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Verify docker-compose.yml settings"
echo "2. Run: docker compose up -d"
echo "3. Monitor startup: docker compose logs -f"
echo ""
echo "Services will be available at:"
echo "  - Nginx:      https://localhost"
echo "  - Pi-hole:    http://localhost/admin"
echo "  - Kibana:     http://localhost:5601"
echo "  - Elasticsearch: http://localhost:9200"
echo ""
