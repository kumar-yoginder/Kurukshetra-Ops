#!/bin/bash

# Kurukshetra-Ops Post-Deployment Setup
# Initializes Kibana dashboards and Elasticsearch pipelines
# Run this after 'docker compose up -d' and services are healthy

set -e

echo "=========================================="
echo "Kurukshetra-Ops Post-Deployment Setup"
echo "=========================================="
echo ""

# Wait for services to be healthy
echo "Waiting for services to be ready..."
echo ""

# Check Elasticsearch via Nginx proxy
echo "Checking Elasticsearch (via Nginx proxy)..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -sk https://localhost/elastic/_cluster/health > /dev/null 2>&1; then
        echo "✓ Elasticsearch is ready"
        break
    fi
    attempt=$((attempt + 1))
    echo "  Waiting... (attempt $attempt/$max_attempts)"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Elasticsearch did not become ready in time"
    exit 1
fi

# Check Kibana via Nginx proxy
echo "Checking Kibana (via Nginx proxy)..."
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -sk https://localhost/kibana/api/status > /dev/null 2>&1; then
        echo "✓ Kibana is ready"
        break
    fi
    attempt=$((attempt + 1))
    echo "  Waiting... (attempt $attempt/$max_attempts)"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Kibana did not become ready in time"
    exit 1
fi

# Check Filebeat
echo "Checking Filebeat..."
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker exec filebeat filebeat test output > /dev/null 2>&1; then
        echo "✓ Filebeat is ready"
        break
    fi
    attempt=$((attempt + 1))
    echo "  Waiting... (attempt $attempt/$max_attempts)"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Filebeat did not become ready in time"
    exit 1
fi

echo ""
echo "=========================================="
echo "All services healthy. Proceeding with setup..."
echo "=========================================="
echo ""

# Step 1: Load Nginx Dashboards
echo "Step 1: Loading Nginx dashboards..."
if docker exec -it filebeat filebeat setup --dashboards; then
    echo "✓ Nginx dashboards loaded successfully"
else
    echo "⚠️  Warning: Failed to load Nginx dashboards"
    echo "   You can run manually: docker exec -it filebeat filebeat setup --dashboards"
fi

echo ""

# Step 2: Create Pi-hole Ingest Pipeline
echo "Step 2: Creating Pi-hole Elasticsearch ingest pipeline..."
PIPELINE_RESPONSE=$(curl -sk -X PUT "https://localhost/elastic/_ingest/pipeline/pihole-pipeline" \
  -H 'Content-Type: application/json' \
  -d '{
  "description": "Pi-hole log parser with ECS fix",
  "processors": [
    {
      "grok": {
        "field": "message",
        "patterns": ["%{SYSLOGTIMESTAMP:timestamp} %{DATA:temp_process}\\[%{NUMBER:pid}\\]: %{WORD:action} %{IPORHOST:domain} is %{IP:ip}"],
        "ignore_missing": true
      }
    },
    {
      "rename": {
        "field": "temp_process",
        "target_field": "process.name",
        "ignore_missing": true
      }
    },
    {
      "remove": {
        "field": "pid",
        "ignore_missing": true
      }
    }
  ]
}')

if echo "$PIPELINE_RESPONSE" | grep -q '"acknowledged":true'; then
    echo "✓ Pi-hole pipeline created successfully"
else
    echo "⚠️  Pipeline response: $PIPELINE_RESPONSE"
fi

echo ""
echo "=========================================="
echo "Setup Complete! ✓"
echo "=========================================="
echo ""
echo "Available dashboards and pipelines:"
echo "  - Kibana Dashboards: https://localhost/kibana"
echo "    - Nginx access & error logs"
echo "    - System logs"
echo "    - Pi-hole logs"
echo ""
echo "  - Elasticsearch API: https://localhost/elastic"
echo "    - pihole-pipeline: Custom Pi-hole log parser"
echo ""
echo "  - Pi-hole Admin: https://localhost/admin"
echo ""
echo "Next steps:"
echo "1. Visit Kibana: https://localhost/kibana"
echo "2. Create index patterns for:"
echo "    - filebeat-*"
echo "    - pihole-*"
echo "3. Explore dashboards under 'Analytics > Dashboards'"
echo ""
